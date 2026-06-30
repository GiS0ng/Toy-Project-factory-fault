import sys
import os

# 모듈들의 상대경로 임포트가 꼬이지 않도록 파이썬 환경(sys.path)에 현재 디렉토리를 주입합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from network.socket_server import SmartFactoryBridge

if __name__ == "__main__":
    try:
        # 캡슐화된 전체 엔진을 단 두 줄로 인스턴스화하고 시작합니다.
        bridge_server = SmartFactoryBridge()
        bridge_server.start()
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")