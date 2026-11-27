"""Zamanlanmış araştırma işi (tek yazıcı). GitHub Actions ve elle çalıştırma için giriş noktası."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vr import runner  # noqa: E402

if __name__ == "__main__":
    try:
        print(json.dumps(runner.run(), ensure_ascii=False, default=str))
    except RuntimeError as e:
        print(f"Atlandı/durduruldu: {e}")
        sys.exit(1)
