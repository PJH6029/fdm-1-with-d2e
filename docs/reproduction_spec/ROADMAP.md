1. e2e pipeline 구성
2. video encoder: 가지고 있는 모든 비디오를 총동원해서, game domain knowledge를 반영하는 video encoder 구축
3. IDM ablation: FDM-1 방식을 기본으로 하여, labeled video를 가지고 IDM pretraining
4. pseudo-label 생성: 추가 데이터를 pseudo-label
5. FDM 학습: labeled-only vs pseudo-label only vs both ablation, FDM architecture ablation
6. e2e evaluation: 전체 성능 뽑아내기
7. plug-and-play SDK