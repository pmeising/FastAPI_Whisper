from fastapi import FastAPI, UploadFile, File
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import tempfile
import os
import time
import logging
import warnings
import librosa
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Filter out specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torchaudio")
warnings.filterwarnings("ignore", message=".*forced_decoder_ids.*")
warnings.filterwarnings("ignore", message=".*multilingual Whisper.*")

# Prometheus metrics
TRANSCRIPTION_REQUESTS = Counter('whisper_transcription_requests_total', 'Total transcription requests')
TRANSCRIPTION_DURATION = Histogram('whisper_transcription_duration_seconds', 'Time spent on transcription')
INFERENCE_DURATION = Histogram('whisper_inference_duration_seconds', 'Time spent on model inference')
AUDIO_LOAD_DURATION = Histogram('whisper_audio_load_duration_seconds', 'Time spent loading audio')
PROCESSING_DURATION = Histogram('whisper_processing_duration_seconds', 'Time spent processing audio')
DECODE_DURATION = Histogram('whisper_decode_duration_seconds', 'Time spent decoding results')
TRANSCRIPTION_ERRORS = Counter('whisper_transcription_errors_total', 'Total transcription errors')
MODEL_LOADED = Gauge('whisper_model_loaded', 'Whether the model is loaded (1) or not (0)')

# Initialize FastAPI app
app = FastAPI()

# Global variables for model and processor
whisper_model = None
processor = None

def load_whisper_model():
    """Load Whisper Large V3 model using transformers library"""
    global whisper_model, processor
    try:
        logger.info("Loading Whisper Large V3 model...")
        # Load the model and processor from Hugging Face
        model_name = "openai/whisper-large-v3-turbo"
        processor = WhisperProcessor.from_pretrained(model_name)
        whisper_model = WhisperForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        
        # Move to GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        whisper_model = whisper_model.to(device)
        
        logger.info(f"Whisper Large V3 model loaded successfully on {device}")
        MODEL_LOADED.set(1)  # Set metric to indicate model is loaded
        return True
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        MODEL_LOADED.set(0)  # Set metric to indicate model failed to load
        return False

# Load model on startup
model_loaded = load_whisper_model()

def load_audio_file(file_path):
    """Load audio file using torchaudio with librosa fallback"""
    try:
        waveform, sample_rate = torchaudio.load(file_path)
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        return waveform.squeeze().numpy()
    except Exception as e:
        logger.warning(f"torchaudio failed: {e}, trying librosa fallback")
        # Fallback to librosa
        waveform, sample_rate = librosa.load(file_path, sr=16000, mono=True)
        return waveform

@app.post("/transcribe/")
async def transcribe(audio_file: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper Large V3 model.
    """
    if not model_loaded or whisper_model is None or processor is None:
        return {"error": "Whisper model not loaded"}
    
    # Increment request counter
    TRANSCRIPTION_REQUESTS.inc()
    
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Save uploaded file temporarily
        file_extension = os.path.splitext(audio_file.filename or "audio.wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name
        
        audio_load_start = time.time()
        # Load audio
        audio = load_audio_file(temp_file_path)
        audio_load_time = time.time() - audio_load_start
        AUDIO_LOAD_DURATION.observe(audio_load_time)
        
        # Process audio for the model
        process_start = time.time()
        inputs = processor(
            audio, 
            sampling_rate=16000, 
            return_tensors="pt",
            language="en",  # Force English to avoid warnings
            task="transcribe"  # Explicit task to avoid warnings
        )
        process_time = time.time() - process_start
        PROCESSING_DURATION.observe(process_time)
        
        # Move inputs to same device as model
        device = next(whisper_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate transcription
        inference_start = time.time()
        with torch.no_grad():
            predicted_ids = whisper_model.generate(
                **inputs,
                attention_mask=inputs.get("attention_mask"),  # Explicit attention mask
                forced_decoder_ids=None,  # Avoid deprecated warning
                suppress_tokens=None
            )
        inference_time = time.time() - inference_start
        INFERENCE_DURATION.observe(inference_time)
        
        # Decode the transcription
        decode_start = time.time()
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        decode_time = time.time() - decode_start
        DECODE_DURATION.observe(decode_time)
        
        total_time = time.time() - start_time
        TRANSCRIPTION_DURATION.observe(total_time)
        
        # Log performance metrics
        logger.info(f"Transcription completed - Total: {total_time:.2f}s, "
                   f"Audio Load: {audio_load_time:.2f}s, "
                   f"Processing: {process_time:.2f}s, "
                   f"Inference: {inference_time:.2f}s, "
                   f"Decode: {decode_time:.2f}s")
        
        # Clean up temporary file
        if temp_file_path:
            os.unlink(temp_file_path)
        
        return {
            "transcription": transcription.strip(),
            "metrics": {
                "total_time": round(total_time, 2),
                "audio_load_time": round(audio_load_time, 2),
                "processing_time": round(process_time, 2),
                "inference_time": round(inference_time, 2),
                "decode_time": round(decode_time, 2),
                "device": str(device)
            }
        }
        
    except Exception as e:
        TRANSCRIPTION_ERRORS.inc()  # Increment error counter
        total_time = time.time() - start_time
        logger.error(f"Transcription failed after {total_time:.2f}s: {str(e)}")
        
        # Clean up temporary file if it exists
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
        return {"error": f"Transcription failed: {str(e)}"}

@app.get("/")
def root():
    """
    Health check endpoint.
    """
    model_status = "loaded" if model_loaded else "failed to load"
    return {"message": f"Whisper Large V3 Speech-to-Text API is up and running! Model status: {model_status}"}

@app.get("/health")
def health_check():
    """
    Detailed health check endpoint.
    """
    return {
        "status": "healthy" if model_loaded else "unhealthy",
        "model_loaded": model_loaded,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }

@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)