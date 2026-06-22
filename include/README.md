└── 프로젝트 루트 폴더
     ├── include/
       ├── ErrorCode.h
       ├── IVibrationSensor.h
       └── MachineMonitor.h


        ##ErrorCode.H
          1. Type : 열거형 데이터 타입 
          2. CSV 포맷 데이터 형태 
          3. 상태코드  
            NORMAL : 정상 운전상태 , NEED_INSPECRION : 육안 점검 필요 상태 , IMMEDIATE_STOP : 치명적인 진동 오류 감지


        ##IVibrationSensor.h
          1. class VibrationSensor: 실제 공장 장비에 장착된 물리적인 진동 측정 센서를 프로그램 안에서 하나의 '물체(객체)'로 다루기 위해 선언한 클래스
          2. getVibration() :이 센서의 가장 핵심적인 기능

        ##MachineMonitor.h
          1.VibrationLog :데이터 보관함 양식
          2.std::vector<VibrationLog> periodic_buffer: 버퍼를 이용해 오류 발생시 이전 정상데이터 저장
          3.VibrationSensor,및 내부 함수 선언 
          4. runTestScenario(): 가상 테스트 함수 
