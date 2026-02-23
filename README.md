# SmartX PPE Detection 🦺

Sistema de detecção de EPI em tempo real usando **YOLOv8** + **FastAPI**.

## EPIs Detectados
| EPI | Classe | Violação |
|-----|--------|----------|
| Capacete | `Hardhat` | `NO-Hardhat` |
| Colete de segurança | `Safety Vest` | `NO-Safety Vest` |
| Máscara | `Mask` | `NO-Mask` |
| Pessoa | `Person` | — |

---

## Instalação

```bash
# 1. Clone / extraia o projeto
cd ppe-detection

# 2. Crie ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instale dependências
pip install -r requirements.txt
```

---

## Uso

### Opção 1 — Interface Web (câmera via browser)
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Acesse: **http://localhost:8000**

- Clique em **"Iniciar Câmera"** para começar a detecção
- Configure quais EPIs são obrigatórios no painel lateral
- Veja status em tempo real: ✓ CONFORME / ⚠ NÃO CONFORME

### Opção 2 — Câmera local (janela OpenCV)
```bash
python run_camera.py
```
- Pressione `Q` para sair
- Pressione `S` para salvar screenshot

---

## API REST

### GET /health
```json
{
  "status": "ok",
  "model": "best.pt",
  "classes": ["Hardhat", "Safety Vest", ...]
}
```

### POST /detect/image
Upload de imagem (multipart/form-data):
```bash
curl -X POST http://localhost:8000/detect/image \
  -F "file=@foto.jpg"
```
Retorno:
```json
{
  "detections": [
    { "class": "Hardhat", "confidence": 0.92, "bbox": {...}, "is_violation": false }
  ],
  "compliance": true,
  "missing_ppe": [],
  "ppe_detected": ["Hardhat", "Safety Vest"]
}
```

### POST /detect/base64
```json
{
  "image": "<base64_string>",
  "required_ppe": ["Hardhat", "Safety Vest"]
}
```

### WS /ws/camera
WebSocket para stream em tempo real. Envie frames base64 e receba detecções.

---

## Modelo

O sistema usa por padrão o modelo **`keremberke/yolov8n-ppe-detection`** do Hugging Face,
baixado automaticamente na primeira execução (~6MB).

Para usar um modelo customizado:
```python
detector = PPEDetector(model_path="meu_modelo.pt")
```

### Treinar modelo customizado
```bash
# Instale datasets de PPE do Roboflow
pip install roboflow

# Treine com seus próprios dados
yolo train data=ppe_dataset.yaml model=yolov8n.pt epochs=50 imgsz=640
```

---

## Estrutura do Projeto
```
ppe-detection/
├── app/
│   ├── main.py          # FastAPI + WebSocket
│   └── detector.py      # Lógica de detecção YOLOv8
├── static/
│   └── index.html       # Interface web
├── run_camera.py         # Script câmera local
├── requirements.txt
└── README.md
```
