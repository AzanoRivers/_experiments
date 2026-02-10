# Optimizador y Convertidor de PDFs a WebP

Sistema 100% Python para convertir PDFs a imágenes WebP optimizadas con detección automática de datos sensibles mediante OCR con GPU.

## 🚀 Instalación

### Primera vez (instalación completa):

```powershell
.\install.bat
```

Este script:
1. ✅ Crea el entorno virtual `.venv_new`
2. ✅ Instala todas las dependencias
3. ✅ Configura PyTorch con soporte GPU (CUDA)

### Reinstalación manual (si necesitas):

```powershell
# Solo dependencias principales
.\.venv_new\Scripts\python.exe -m pip install -r requirements.txt

# PyTorch con GPU
.\.venv_new\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

## 🎯 Uso Rápido

```powershell
.\run.bat
```

1. Coloca tus PDFs en `pdfs/`
2. Ejecuta `run.bat`
3. Encuentra las imágenes en `output/`

## ⚙️ Configuración (.env)

```env
CEDULA=xxxx
CELULAR=xxxxxx
CODIGO=xxxx
QUALITY=75
DPI=150
```

## ✨ Características

- ✅ **OCR con GPU** - Detección rápida con tu NVIDIA GPU
- ✅ **Censura precisa** - Solo en coordenadas exactas
- ✅ **Ultra optimizado** - 100-300 KB por imagen
- ✅ **PDFs nativos y escaneados** - Detecta ambos tipos
- ✅ **100% aislado** - Todo en `.venv_new`

## 📦 Dependencias (auto-instaladas)

- Pillow 12.1.0
- PyMuPDF 1.26.7
- EasyOCR 1.7.2
- PyTorch (CUDA)
- NumPy 2.4.2

**Tamaño total**: ~2.7 GB (incluye PyTorch con CUDA)

## 💡 Solución rápida de problemas

**Reinstalar todo:**
```powershell
Remove-Item -Recurse -Force .venv_new
.\install.bat
```

**GPU no detectada:**
```powershell
.\.venv_new\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**Imágenes muy pesadas:**
Edita `.env`: `QUALITY=70` y/o `DPI=120`
