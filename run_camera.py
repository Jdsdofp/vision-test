"""
run_camera.py - Abre câmera local e mostra detecção em tempo real
Execute: python run_camera.py
"""

import cv2
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.detector import PPEDetector

def main():
    print("🔄 Iniciando SmartX PPE Detection...")
    print("📋 EPIs detectados: Capacete, Colete, Máscara")
    print("⌨️  Pressione 'Q' para sair | 'S' para salvar screenshot\n")

    detector = PPEDetector(confidence=0.45)

    # Detecta câmeras disponíveis (tenta DirectShow no Windows primeiro)
    import platform
    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY

    cap = None
    for idx in range(5):
        test = cv2.VideoCapture(idx, backend)
        if test.isOpened():
            ret, _ = test.read()
            if ret:
                print(f"✅ Câmera encontrada no índice {idx}")
                cap = test
                break
            test.release()

    if cap is None or not cap.isOpened():
        print("❌ Nenhuma câmera disponível.")
        print("   Verifique se a câmera está conectada e não está em uso por outro programa.")
        return

    # Configurações de resolução
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("✅ Câmera aberta! Iniciando detecção...")

    frame_count = 0
    screenshot_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Falha ao capturar frame")
            break

        frame_count += 1

        # Detecta a cada 2 frames para melhor performance
        if frame_count % 2 == 0:
            result = detector.detect(frame)
            annotated = result["annotated_frame"]

            # Info lateral
            h, w = annotated.shape[:2]
            info_x = w - 280

            # Painel de info
            overlay = annotated.copy()
            cv2.rectangle(overlay, (info_x - 10, 45), (w - 5, 45 + 140), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

            y = 65
            cv2.putText(annotated, "EPIs DETECTADOS:", (info_x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            ppe_items = [d['class'] for d in result['detections'] if not d['is_violation']]
            if ppe_items:
                for item in ppe_items[:5]:
                    y += 20
                    cv2.putText(annotated, f"  ✓ {item}", (info_x, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 100), 1)
            else:
                y += 20
                cv2.putText(annotated, "  Nenhum EPI", (info_x, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

            y += 25
            violation_color = (0, 80, 255) if result['violations'] else (100, 100, 100)
            cv2.putText(annotated, f"VIOLACOES: {len(result['violations'])}", (info_x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, violation_color, 1)

            cv2.imshow("SmartX PPE Detection - [Q] Sair [S] Screenshot", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('s') or key == ord('S'):
            screenshot_count += 1
            filename = f"screenshot_{screenshot_count:03d}.jpg"
            cv2.imwrite(filename, annotated)
            print(f"📸 Screenshot salvo: {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("✅ Detecção encerrada.")


if __name__ == "__main__":
    main()
