"""
PPE Detector - Core de detecção usando YOLOv8
Suporta modelo pré-treinado ou modelo customizado
"""

import cv2
import numpy as np
from typing import Optional
import os

# Mapeamento de classes PPE (modelo keremberke/yolov8n-ppe-detection)
PPE_CLASS_MAP = {
    0: "Hardhat",      # Capacete
    1: "Mask",         # Máscara
    2: "NO-Hardhat",   # SEM capacete ⚠️
    3: "NO-Mask",      # SEM máscara ⚠️
    4: "NO-Safety Vest", # SEM colete ⚠️
    5: "Person",       # Pessoa detectada
    6: "Safety Cone",  # Cone de segurança
    7: "Safety Vest",  # Colete de segurança
    8: "Machinery",    # Maquinário
    9: "Vehicle",      # Veículo
}

# Classes de violação (sem EPI)
VIOLATION_CLASSES = {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}

# Cores por tipo (BGR)
CLASS_COLORS = {
    "Hardhat": (0, 255, 0),         # Verde
    "Safety Vest": (0, 255, 128),   # Verde claro
    "Mask": (0, 200, 255),          # Ciano
    "NO-Hardhat": (0, 0, 255),      # Vermelho
    "NO-Mask": (0, 0, 255),         # Vermelho
    "NO-Safety Vest": (0, 0, 255),  # Vermelho
    "Person": (255, 128, 0),        # Laranja
    "Safety Cone": (0, 165, 255),   # Laranja
    "Machinery": (128, 0, 128),     # Roxo
    "Vehicle": (128, 128, 0),       # Amarelo escuro
}


class PPEDetector:
    def __init__(self, model_path: Optional[str] = None, confidence: float = 0.5):
        """
        Inicializa o detector de EPI.
        
        Args:
            model_path: Caminho para modelo .pt customizado. 
                        Se None, baixa modelo PPE pré-treinado.
            confidence: Limiar de confiança (0-1)
        """
        self.confidence = confidence
        self.model = None
        self.model_name = ""
        self.ppe_classes = list(PPE_CLASS_MAP.values())
        
        self._load_model(model_path)

    def _load_model(self, model_path: Optional[str]):
        """Carrega modelo YOLOv8"""
        try:
            from ultralytics import YOLO

            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
                self.model_name = os.path.basename(model_path)
                print(f"✅ Modelo customizado carregado: {self.model_name}")
            else:
                # Modelo PPE pré-treinado do Hugging Face
                # Alternativa: usar yolov8n.pt genérico
                model_file = "ppe_model.pt"
                
                if not os.path.exists(model_file):
                    print("⏳ Baixando modelo PPE pré-treinado...")
                    try:
                        from huggingface_hub import hf_hub_download
                        model_file = hf_hub_download(
                            repo_id="keremberke/yolov8n-ppe-detection",
                            filename="best.pt"
                        )
                        print(f"✅ Modelo baixado: {model_file}")
                    except Exception:
                        print("⚠️  Hugging Face indisponível. Usando YOLOv8n genérico.")
                        model_file = "yolov8n.pt"

                self.model = YOLO(model_file)
                self.model_name = model_file

            # Atualiza classes conforme modelo carregado
            if hasattr(self.model, 'names'):
                self.ppe_classes = list(self.model.names.values())

        except ImportError:
            print("❌ ultralytics não instalado. Execute: pip install ultralytics")
            raise

    def detect(self, frame: np.ndarray, required_ppe: Optional[list] = None) -> dict:
        """
        Detecta EPIs no frame.
        
        Args:
            frame: Frame OpenCV (BGR)
            required_ppe: Lista de EPIs obrigatórios ex: ["Hardhat", "Safety Vest"]
        
        Returns:
            dict com detections, compliance, missing_ppe, annotated_frame
        """
        if self.model is None:
            return self._empty_result(frame)

        results = self.model(frame, conf=self.confidence, verbose=False)[0]
        
        detections = []
        detected_classes = set()
        has_person = False

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # Nome da classe
            if hasattr(self.model, 'names'):
                class_name = self.model.names[cls_id]
            else:
                class_name = PPE_CLASS_MAP.get(cls_id, f"class_{cls_id}")

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            detections.append({
                "class": class_name,
                "confidence": round(conf, 3),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "is_violation": class_name in VIOLATION_CLASSES
            })

            detected_classes.add(class_name)
            if class_name == "Person":
                has_person = True

        # Calcula conformidade
        ppe_present = [d["class"] for d in detections if d["class"] not in VIOLATION_CLASSES and d["class"] != "Person"]
        violations = [d["class"] for d in detections if d["is_violation"]]

        if required_ppe:
            missing = [p for p in required_ppe if p not in detected_classes]
        else:
            missing = violations

        compliance = len(violations) == 0 and has_person

        # Anota o frame
        annotated = self._annotate_frame(frame.copy(), detections, compliance, violations)

        return {
            "detections": detections,
            "compliance": compliance,
            "missing_ppe": missing,
            "ppe_detected": ppe_present,
            "violations": violations,
            "person_detected": has_person,
            "annotated_frame": annotated
        }

    def _annotate_frame(self, frame: np.ndarray, detections: list, compliance: bool, violations: list) -> np.ndarray:
        """Desenha bounding boxes e informações no frame"""
        h, w = frame.shape[:2]

        for det in detections:
            bbox = det["bbox"]
            cls = det["class"]
            conf = det["confidence"]
            
            color = CLASS_COLORS.get(cls, (200, 200, 200))
            thickness = 3 if det["is_violation"] else 2

            # Bounding box
            cv2.rectangle(frame, (bbox["x1"], bbox["y1"]), (bbox["x2"], bbox["y2"]), color, thickness)

            # Label com fundo
            label = f"{cls} {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (bbox["x1"], bbox["y1"] - th - 8), (bbox["x1"] + tw + 4, bbox["y1"]), color, -1)
            cv2.putText(frame, label, (bbox["x1"] + 2, bbox["y1"] - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Status banner no topo
        if violations:
            banner_color = (0, 0, 200)
            status_text = f"⚠ NAO CONFORME - {', '.join(violations)}"
        elif compliance:
            banner_color = (0, 150, 0)
            status_text = "✓ CONFORME - Todos EPIs detectados"
        else:
            banner_color = (50, 50, 50)
            status_text = "Aguardando pessoa..."

        cv2.rectangle(frame, (0, 0), (w, 40), banner_color, -1)
        cv2.putText(frame, status_text, (10, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame

    def _empty_result(self, frame):
        return {
            "detections": [],
            "compliance": False,
            "missing_ppe": [],
            "ppe_detected": [],
            "violations": [],
            "person_detected": False,
            "annotated_frame": frame
        }
