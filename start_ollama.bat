@echo off
REM ============================================================
REM  Launch Ollama — RTX 4060 Laptop GPU (8 GB VRAM)
REM ============================================================
REM  nvidia-smi confirms:
REM    CUDA 0 = RTX 4060 Laptop GPU  (8 GB)
REM
REM  Key env vars:
REM    CUDA_VISIBLE_DEVICES=0    — use only the 4060
REM    OLLAMA_NUM_GPU=999        — offload ALL layers to GPU (max)
REM    OLLAMA_GPU_OVERHEAD=300M  — reserve 300MB for OS/display, use rest
REM    OLLAMA_FLASH_ATTENTION=1  — less VRAM usage with flash attn
REM ============================================================

set CUDA_VISIBLE_DEVICES=0
set OLLAMA_NUM_GPU=999
set OLLAMA_GPU_OVERHEAD=314572800
set OLLAMA_FLASH_ATTENTION=1

echo ============================================================
echo  Genoresearch — Ollama GPU Launcher
echo ============================================================
echo  GPU:                  RTX 4060 Laptop (8 GB)
echo  CUDA_VISIBLE_DEVICES: %CUDA_VISIBLE_DEVICES%
echo  OLLAMA_NUM_GPU:       %OLLAMA_NUM_GPU% (all layers)
echo  OLLAMA_GPU_OVERHEAD:  300 MB reserved
echo  OLLAMA_FLASH_ATTENTION: ON
echo ============================================================
echo.

ollama serve
