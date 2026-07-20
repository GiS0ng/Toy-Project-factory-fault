import os
import sys

# 실행 위치와 관계없이 내부 모듈을 가져올 수 있도록 경로를 추가한다.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from network.socket_server import SmartFactoryBridge


if __name__ == "__main__":
    try:
        # 전체 브리지 서버를 생성하고 실행한다.
        bridge_server = SmartFactoryBridge()
        bridge_server.start()
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")
