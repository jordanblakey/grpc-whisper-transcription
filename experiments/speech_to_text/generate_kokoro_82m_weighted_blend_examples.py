import os
import torch
import soundfile as sf
from kokoro import KPipeline

# 1. Initialize
pipeline = KPipeline(lang_code='a')
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# --- THE SMART PATCH ---
# Save the original method so we can still use it for base voices
original_load_single_voice = pipeline.load_single_voice

def smart_load_voice(voice):
    local_path = f'voices/{voice}.pt'
    
    # Check if it's one of your custom remixes first
    if os.path.exists(local_path):
        print(f"   📂 Loading custom remix: {local_path}")
        return torch.load(local_path, weights_only=True).to(device)
    
    # If it's not local, use the original downloader for base voices (sarah, emma, etc.)
    print(f"   🌐 Fetching base voice from cache/cloud: {voice}")
    return original_load_single_voice(voice)

# Apply the patch
pipeline.load_single_voice = smart_load_voice
# -----------------------

# 2. Setup Directories
os.makedirs('voices', exist_ok=True)
base_output_dir = "generated_audio"

# 3. Create and Save Blends
remixes = {
    "Mid_Atlantic": {"af_sarah": 0.5, "bf_emma": 0.5},
    "Gravel_Radio": {"am_michael": 0.6, "bm_george": 0.4}
}

for name, weights in remixes.items():
    print(f"\n🛠️ Creating Remix: {name}")
    mixed_tensor = None
    for v_name, weight in weights.items():
        # This now uses our smart_load_voice to get the base tensors
        voice_tensor = pipeline.load_voice(v_name).to(device)
        if mixed_tensor is None:
            mixed_tensor = voice_tensor * weight
        else:
            mixed_tensor += voice_tensor * weight
    
    torch.save(mixed_tensor, f'voices/{name}.pt')

# 4. Generate
text = "The sixth sick sheik's sixth sheep's sick."
for name in remixes.keys():
    print(f"🎤 Testing: {name}")
    generator = pipeline(text, voice=name, speed=1.1)
    os.makedirs(f"{base_output_dir}/kokoro_82m_weighted_blends", exist_ok=True)
    for gs, ps, audio in generator:
        out_path = f"{base_output_dir}/kokoro_82m_weighted_blends/{name}_twister.wav"
        sf.write(out_path, audio, 24000)
        print(f"✅ Saved {out_path}")