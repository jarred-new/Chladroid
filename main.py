import math
import random
import pygame

# ------------------------------------------------------------
# Optional Android / PyJNIus support
# ------------------------------------------------------------

ANDROID = False

try:
    from jnius import autoclass
    ANDROID = True
except Exception:
    ANDROID = False


# ------------------------------------------------------------
# Application constants
# ------------------------------------------------------------

APP_NAME = "Chladroid"

BACKGROUND_COLOR = (20, 20, 25)
SAND_COLOR = (245, 222, 179)
TEXT_COLOR = (220, 220, 220)

# Start with a reasonable Android particle count.
# Increase later if performance is good.
NUM_PARTICLES = 8000

VIBRATION_STRENGTH = 12.0

SAMPLE_RATE = 44100

# AudioRecord uses 16-bit PCM.
PCM_MAX = 32767.0


# ------------------------------------------------------------
# Android audio state
# ------------------------------------------------------------

recorder = None
audio_buffer = None
buffer_elements = 0
audio_available = False

AudioRecord = None
AudioFormat = None
AudioSource = None


# ------------------------------------------------------------
# Android class initialization
# ------------------------------------------------------------

def load_android_audio_classes():
    """
    Loads Android Java classes lazily.

    IMPORTANT:
    This is deliberately NOT executed at module import time.
    """

    global AudioRecord
    global AudioFormat
    global AudioSource

    if not ANDROID:
        return False

    try:
        AudioRecord = autoclass("android.media.AudioRecord")
        AudioFormat = autoclass("android.media.AudioFormat")
        AudioSource = autoclass(
            "android.media.MediaRecorder$AudioSource"
        )

        return True

    except Exception as exc:
        print("[Chladroid] Failed to load Android audio classes:")
        print(repr(exc))

        AudioRecord = None
        AudioFormat = None
        AudioSource = None

        return False


# ------------------------------------------------------------
# Android microphone initialization
# ------------------------------------------------------------

def initialize_audio():
    """
    Safely initializes Android AudioRecord.

    Failure of microphone initialization should NOT crash
    the entire application.
    """

    global recorder
    global audio_buffer
    global buffer_elements
    global audio_available

    audio_available = False
    recorder = None
    audio_buffer = None
    buffer_elements = 0

    if not ANDROID:
        print("[Chladroid] Android audio unavailable.")
        return False

    if not load_android_audio_classes():
        return False

    try:
        channel_config = AudioFormat.CHANNEL_IN_MONO
        audio_format = AudioFormat.ENCODING_PCM_16BIT

        min_buffer_size = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            channel_config,
            audio_format
        )

        print(
            "[Chladroid] AudioRecord minimum buffer:",
            min_buffer_size
        )

        # Android returns a negative value when the configuration
        # is unsupported.
        if min_buffer_size <= 0:
            print(
                "[Chladroid] AudioRecord returned invalid buffer size."
            )
            return False

        # Give AudioRecord some extra room.
        audio_buffer_size = max(
            min_buffer_size * 2,
            4096
        )

        # Number of 16-bit samples.
        buffer_elements = audio_buffer_size // 2

        recorder = AudioRecord(
            AudioSource.MIC,
            SAMPLE_RATE,
            channel_config,
            audio_format,
            audio_buffer_size
        )

        # Verify that Android actually initialized the recorder.
        if recorder.getState() != AudioRecord.STATE_INITIALIZED:
            print(
                "[Chladroid] AudioRecord STATE_INITIALIZED check failed."
            )

            try:
                recorder.release()
            except Exception:
                pass

            recorder = None
            return False

        audio_buffer = [0] * buffer_elements

        try:
            recorder.startRecording()
        except Exception as exc:
            print(
                "[Chladroid] startRecording() failed:",
                repr(exc)
            )

            try:
                recorder.release()
            except Exception:
                pass

            recorder = None
            audio_buffer = None

            return False

        # Check recording state.
        if (
            recorder.getRecordingState()
            != AudioRecord.RECORDSTATE_RECORDING
        ):
            print(
                "[Chladroid] AudioRecord did not enter recording state."
            )

            try:
                recorder.stop()
            except Exception:
                pass

            try:
                recorder.release()
            except Exception:
                pass

            recorder = None
            audio_buffer = None

            return False

        audio_available = True

        print("[Chladroid] Microphone initialized successfully.")

        return True

    except Exception as exc:
        print("[Chladroid] Microphone initialization failed:")
        print(repr(exc))

        if recorder is not None:
            try:
                recorder.release()
            except Exception:
                pass

        recorder = None
        audio_buffer = None
        buffer_elements = 0
        audio_available = False

        return False


# ------------------------------------------------------------
# Audio shutdown
# ------------------------------------------------------------

def shutdown_audio():
    """
    Stops and releases AudioRecord safely.
    """

    global recorder
    global audio_buffer
    global buffer_elements
    global audio_available

    audio_available = False

    if recorder is not None:

        try:
            recorder.stop()
        except Exception:
            pass

        try:
            recorder.release()
        except Exception:
            pass

    recorder = None
    audio_buffer = None
    buffer_elements = 0

    print("[Chladroid] Audio released.")


# ------------------------------------------------------------
# Microphone level
# ------------------------------------------------------------

def get_decibels():
    """
    Reads microphone samples and calculates RMS dBFS.

    Returns:
        approximately -100.0 to 0.0 dBFS

    A failure returns -100.0 instead of crashing the app.
    """

    if not audio_available:
        return -100.0

    if recorder is None:
        return -100.0

    if audio_buffer is None:
        return -100.0

    if buffer_elements <= 0:
        return -100.0

    try:
        samples_read = recorder.read(
            audio_buffer,
            0,
            buffer_elements
        )

        if samples_read <= 0:
            return -100.0

        # Protect against a Java/PyJNIus return value that is
        # larger than the Python list.
        samples_read = min(
            int(samples_read),
            len(audio_buffer)
        )

        if samples_read <= 0:
            return -100.0

        sum_squares = 0.0

        for i in range(samples_read):
            sample = audio_buffer[i]

            # Convert to Python float before multiplication.
            sample = float(sample)

            sum_squares += sample * sample

        rms = math.sqrt(
            sum_squares / float(samples_read)
        )

        if rms < 1.0:
            return -100.0

        dbfs = 20.0 * math.log10(
            rms / PCM_MAX
        )

        # Clamp the result to a sensible range.
        return max(-100.0, min(0.0, dbfs))

    except Exception as exc:
        print(
            "[Chladroid] Audio read error:",
            repr(exc)
        )

        return -100.0


# ------------------------------------------------------------
# Particle
# ------------------------------------------------------------

class SandParticle:

    __slots__ = (
        "x",
        "y"
    )

    def __init__(self, width, height):
        self.x = 0.0
        self.y = 0.0

        self.reset(width, height)

    def reset(self, width, height):
        """
        Randomly place the particle on the plate.
        """

        if width <= 0:
            width = 1

        if height <= 0:
            height = 1

        self.x = random.uniform(
            0.0,
            float(width - 1)
        )

        self.y = random.uniform(
            0.0,
            float(height - 1)
        )

    def update(
        self,
        n,
        m,
        a,
        b,
        width,
        height
    ):
        """
        Calculates the Chladni wave amplitude and
        moves the particle.
        """

        if width <= 0 or height <= 0:
            return

        nx = self.x / float(width)
        ny = self.y / float(height)

        term_1 = (
            a
            * math.sin(n * math.pi * nx)
            * math.sin(m * math.pi * ny)
        )

        term_2 = (
            b
            * math.sin(m * math.pi * nx)
            * math.sin(n * math.pi * ny)
        )

        amplitude = term_1 + term_2
        abs_amp = abs(amplitude)

        if abs_amp > 0.02:

            force = abs_amp * VIBRATION_STRENGTH

            self.x += random.uniform(
                -force,
                force
            )

            self.y += random.uniform(
                -force,
                force
            )

        # Keep the particle on the plate.
        if (
            self.x < 0.0
            or self.x >= width
            or self.y < 0.0
            or self.y >= height
        ):
            self.reset(width, height)

    def draw(self, surface):
        """
        Draw one particle.
        """

        x = int(self.x)
        y = int(self.y)

        width, height = surface.get_size()

        if (
            0 <= x < width
            and 0 <= y < height
        ):
            surface.set_at(
                (x, y),
                SAND_COLOR
            )


# ------------------------------------------------------------
# Particle initialization
# ------------------------------------------------------------

def create_particles(count, width, height):

    particles = []

    for _ in range(count):
        particles.append(
            SandParticle(
                width,
                height
            )
        )

    return particles


# ------------------------------------------------------------
# Android lifecycle helpers
# ------------------------------------------------------------

def pause_audio():

    global recorder

    if recorder is None:
        return

    try:
        recorder.stop()
    except Exception:
        pass


def resume_audio():

    global recorder
    global audio_available

    if recorder is None:
        return

    try:
        recorder.startRecording()

        if (
            recorder.getRecordingState()
            == AudioRecord.RECORDSTATE_RECORDING
        ):
            audio_available = True

    except Exception as exc:
        print(
            "[Chladroid] Unable to resume microphone:",
            repr(exc)
        )

        audio_available = False


# ------------------------------------------------------------
# Main application
# ------------------------------------------------------------

def main():

    # --------------------------------------------------------
    # Initialize Pygame FIRST.
    # --------------------------------------------------------

    print("[Chladroid] Initializing Pygame...")

    pygame.init()

    # Make sure the display subsystem exists.
    if not pygame.display.get_init():
        print("[Chladroid] Pygame display failed to initialize.")
        pygame.quit()
        return

    try:

        SCREEN = pygame.display.set_mode(
            (0, 0),
            pygame.FULLSCREEN
        )

    except Exception as exc:

        print(
            "[Chladroid] Failed to create display:",
            repr(exc)
        )

        pygame.quit()
        return

    WIDTH, HEIGHT = SCREEN.get_size()

    if WIDTH <= 0 or HEIGHT <= 0:
        WIDTH = 1280
        HEIGHT = 720

        SCREEN = pygame.display.set_mode(
            (WIDTH, HEIGHT),
            pygame.FULLSCREEN
        )

    pygame.display.set_caption(APP_NAME)

    print(
        "[Chladroid] Display:",
        WIDTH,
        "x",
        HEIGHT
    )

    # --------------------------------------------------------
    # Clock
    # --------------------------------------------------------

    CLOCK = pygame.time.Clock()

    # --------------------------------------------------------
    # Font
    # --------------------------------------------------------

    try:
        FONT_SIZE = max(
            24,
            min(54, int(HEIGHT * 0.055))
        )

        FONT = pygame.font.Font(
            None,
            FONT_SIZE
        )

    except Exception:
        FONT = None

    # --------------------------------------------------------
    # Chladni parameters
    # --------------------------------------------------------

    n = 3
    m = 5

    a = 1.0
    b = 1.0

    # --------------------------------------------------------
    # Particles
    # --------------------------------------------------------

    print(
        "[Chladroid] Creating",
        NUM_PARTICLES,
        "particles..."
    )

    particles = create_particles(
        NUM_PARTICLES,
        WIDTH,
        HEIGHT
    )

    print("[Chladroid] Particle system ready.")

    # --------------------------------------------------------
    # Initialize microphone AFTER Pygame.
    #
    # If this fails, the application still runs.
    # --------------------------------------------------------

    print("[Chladroid] Initializing microphone...")

    microphone_ok = initialize_audio()

    if microphone_ok:
        print("[Chladroid] Microphone: OK")
    else:
        print(
            "[Chladroid] Microphone unavailable."
        )
        print(
            "[Chladroid] Running without microphone input."
        )

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------

    running = True

    last_db = -100.0

    # Limit simulation frequency.
    # 10 FPS is considerably more suitable for this
    # Python particle implementation than attempting
    # to run it at 30/60 FPS.
    TARGET_FPS = 10

    while running:

        # ----------------------------------------------------
        # Events
        # ----------------------------------------------------

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.APP_WILLENTERBACKGROUND:

                pause_audio()

            elif event.type == pygame.APP_DIDENTERFOREGROUND:

                resume_audio()

            elif event.type == pygame.VIDEORESIZE:

                try:
                    new_width, new_height = (
                        event.w,
                        event.h
                    )

                    if (
                        new_width > 0
                        and new_height > 0
                    ):
                        WIDTH = new_width
                        HEIGHT = new_height

                        for particle in particles:
                            particle.reset(
                                WIDTH,
                                HEIGHT
                            )

                except Exception as exc:
                    print(
                        "[Chladroid] Resize error:",
                        repr(exc)
                    )

            # Android touch input.
            elif event.type == pygame.FINGERDOWN:

                # Touch currently doesn't modify
                # the simulation, but processing it
                # prevents it from being ignored.
                pass

            elif event.type == pygame.FINGERUP:
                pass

            elif event.type == pygame.FINGERMOTION:
                pass

        # ----------------------------------------------------
        # Microphone
        # ----------------------------------------------------

        current_db = get_decibels()

        # Smooth the displayed value slightly.
        if current_db > -100.0:

            last_db = (
                last_db * 0.70
                + current_db * 0.30
            )

        else:

            last_db = -100.0

        # ----------------------------------------------------
        # Convert microphone level into Chladni modes
        # ----------------------------------------------------

        display_vol = max(
            0,
            min(
                100,
                int(last_db + 100.0)
            )
        )

        # Prevent n/m from ever becoming zero.
        n = max(
            1,
            min(
                20,
                round(display_vol / 14.0)
            )
        )

        m = max(
            1,
            min(
                20,
                round(display_vol / 16.0)
            )
        )

        # ----------------------------------------------------
        # Clear plate
        # ----------------------------------------------------

        SCREEN.fill(BACKGROUND_COLOR)

        # ----------------------------------------------------
        # Update and draw particles
        # ----------------------------------------------------

        for particle in particles:

            particle.update(
                n,
                m,
                a,
                b,
                WIDTH,
                HEIGHT
            )

            particle.draw(SCREEN)

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        if FONT is not None:

            if microphone_ok:
                audio_status = "MIC"
            else:
                audio_status = "NO MIC"

            ui_text = (
                "Chladroid  "
                "n={}  m={}  "
                "dB: {:.1f}  "
                "{}"
            ).format(
                n,
                m,
                last_db,
                audio_status
            )

            text_surface = FONT.render(
                ui_text,
                True,
                TEXT_COLOR
            )

            SCREEN.blit(
                text_surface,
                (15, 15)
            )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        pygame.display.flip()

        CLOCK.tick(TARGET_FPS)

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    shutdown_audio()

    pygame.quit()

    print("[Chladroid] Application closed.")


# ------------------------------------------------------------
# Application entry point
# ------------------------------------------------------------

if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        # Never silently swallow a fatal exception.
        # This is particularly useful when looking at
        # logcat/buildozer output.
        print(
            "[Chladroid] FATAL ERROR:",
            repr(exc)
        )

        try:
            shutdown_audio()
        except Exception:
            pass

        try:
            pygame.quit()
        except Exception:
            pass

        raise