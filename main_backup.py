import pygame
import random
import math

from jnius import autoclass

# Android Audio Recording Class
AudioRecord = autoclass('android.media.AudioRecord')
MediaRecorder = autoclass('android.media.MediaRecorder')
AudioFormat = autoclass('android.media.AudioFormat')
AudioSource = autoclass('android.media.MediaRecorder$AudioSource')

# Recorder Settings
recorder = None
audio_buffer = None
buffer_elements = 0

def init_audio():
    global recorder
    global audio_buffer
    global buffer_elements

    try:
        SAMPLE_RATE = 44100
        CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT

        min_buffer_size = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        )

        if min_buffer_size <= 0:
            print("AudioRecord: invalid buffer size")
            return False

        buffer_elements = min_buffer_size // 2

        recorder = AudioRecord(
            AudioSource.MIC,
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT,
            min_buffer_size
        )

        if recorder.getState() != AudioRecord.STATE_INITIALIZED:
            print("AudioRecord failed to initialize")
            recorder = None
            return False

        audio_buffer = [0] * buffer_elements

        recorder.startRecording()

        if recorder.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING:
            print("AudioRecord failed to start")
            recorder.release()
            recorder = None
            return False

        print("AudioRecord initialized")
        return True

    except Exception as e:
        print("Audio initialization failed:", repr(e))
        recorder = None
        return False

def get_decibels():
    if recorder is None or audio_buffer is None:
        return -100.0

    try:
        samples_read = recorder.read(
            audio_buffer,
            0,
            buffer_elements
        )

        if samples_read <= 0:
            return -100.0

        sum_squares = 0.0

        for i in range(samples_read):
            sample = audio_buffer[i]
            sum_squares += sample * sample

        rms = math.sqrt(sum_squares / samples_read)

        if rms < 1.0:
            return -100.0

        return 20.0 * math.log10(rms / 32767.0)

    except Exception as e:
        print("Audio read error:", repr(e))
        return -100.0
        
def shutdown_audio():
    global recorder

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

def main():
    #pygame.init()
    
    SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = SCREEN.get_size()
    pygame.display.set_caption("Chladroid")
    CLOCK = pygame.time.Clock()
    
    # Colors
    COLOR_BG = (20, 20, 25)       # Dark slate gray plate
    COLOR_SAND = (245, 222, 179)   # Wheat / sand color
    
    # Simulation Hyperparameters
    NUM_PARTICLES = 8000
    VIBRATION_STRENGTH = 15.0
    
    # Chladni Formula Defaults
    # n, m: Mode parameters. a, b: Wave superposition coefficients
    n, m = 3, 5
    a, b = 1.0, 1.0
    
    class SandParticle:
        def __init__(self):
            self.reset()
    
        def reset(self):
            """Randomly scatters particle across the entire plate surface."""
            self.x = random.uniform(0, WIDTH)
            self.y = random.uniform(0, HEIGHT)
    
        def update(self, n, m, a, b):
            """Calculates vibration amplitude at current location and jitters the particle."""
            # Normalize window space coordinates to a [0, 1] range for math stability
            nx = self.x / WIDTH
            ny = self.y / HEIGHT
            # 2D Chladni Wave Equation
            term_1 = a * math.sin(n * math.pi * nx) * math.sin(m * math.pi * ny)
            term_2 = b * math.sin(m * math.pi * nx) * math.sin(n * math.pi * ny)
            amplitude = term_1 + term_2
    
            # Absolute value measures total displacement magnitude from equilibrium
            abs_amp = abs(amplitude)
    
            # Apply random physical displacement proportional to local vibration amplitude
            # Particles near nodes (abs_amp ~ 0) don't move. Near antinodes, they bounce wildly.
            if abs_amp > 0.02:
                force = abs_amp * VIBRATION_STRENGTH
                self.x += random.uniform(-force, force)
                self.y += random.uniform(-force, force)
    
            # Boundary constraints: Keep sand on the plate or reset if pushed off edge
            if self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT:
                self.reset()
    
        def draw(self, surface):
            """Renders single sand grain."""
            # Integer conversion is mandatory for window coordinate indexing
            surface.set_at((int(self.x), int(self.y)), COLOR_SAND)
    
    
    # INITIALIZATION
    particles = [SandParticle() for _ in range(NUM_PARTICLES)]
    
    
    # CORE ENGINE LOOP
    running = True
    while running:
        SCREEN.fill(COLOR_BG)
    
        # Process input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.VIDEORESIZE:
            	WIDTH, HEIGHT = SCREEN.get_size() # refresh on screen
            	for particle in particles:
            		particle.reset()
            
    
        # Dynamic UI Overlay Information
        font = pygame.font.SysFont("Arial", 54)
        ui_text = font.render(f"Loudness: (n={n}, m={m}) ", True, (200, 200, 200))
        SCREEN.blit(ui_text, (15, 15))
    
        # Fetch current Decibel level
        current_db = get_decibels()
        
        # Format value to clean visual scale
        # Scales the raw negative dBFS (-100 to 0) up into a positive 0-100 index range
        display_vol = max(0, int(current_db + 100))
        
        n = max(1, min(20, round(display_vol / 14)))
        
        m = max(1, min(20, round(display_vol / 16)))
        # Create target surface specifically for particle drawing optimization
        for particle in particles:
            particle.update(n, m, a, b)
            particle.draw(SCREEN)
    
        pygame.display.flip()
        CLOCK.tick(60)
    
    #pygame.quit()
    
if __name__ == "__main__":
    pygame.init()

    init_audio()

    try:
        main()
    finally:
        shutdown_audio()
        pygame.quit()