---
language:
- en
license: apache-2.0
library_name: peft
tags:
- vertex-coders
- vision-language-model
- math-reasoning
- unsloth
- qwen2.5-vl
datasets:
- MathLLMs/MathVision
---

# Vertex-Math-Vision (Multimodal Mathematical Reasoning Engine)

**Author:** Denis Sanchez Leyva  
**Organization:** Vertex Coders LLC (Miami, FL)  
**Architecture:** Vision-Language Model (VLM) QLoRA Adapter (`Qwen2.5-VL-7B-Instruct`)

## Overview
**Vertex-Math-Vision** is a specialized multimodal reasoning model engineered by **Vertex Coders LLC**. Fine-tuned on the `MathLLMs/MathVision` benchmark, it bridges visual perception and symbolic deduction—capable of parsing geometric figures, combinatorial graphs, and mathematical diagrams to produce rigorous step-by-step LaTeX solutions.

## Training Architecture & Security Hardening
- **Joint Multimodal Adaptation:** Unlike standard text-only LoRAs, this adapter targets both the Vision Tower (`finetune_vision_layers=True`), the Multimodal Projector, and the Language Model backbone (`r=16`, `alpha=16`).
- **Memory & Payload Hardening:** Implements strict image decompression boundaries (`MAX_IMAGE_PIXELS`), RGB normalization, and dynamic Lanczos downscaling ($768 \times 768$ max envelope) to prevent VRAM exhaustion (OOM) and malicious image payload attacks during ingestion.
- **Optimization:** Trained in 4-bit NormalFloat (`nf4`) with Unsloth custom Triton kernels and 8-bit AdamW optimizer.

## Quickstart Guide

### 1. Environment Setup
```bash
git clone [https://github.com/vertex-coders/vertex-math-vision.git](https://github.com/vertex-coders/vertex-math-vision.git)
cd vertex-math-vision
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env