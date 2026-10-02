# 2x DGX Spark Quality Bench — Core60

**두 개의 DGX Spark에서 로컬 LLM endpoint를 같은 문제와 채점 기준으로 비교하는 자체 회귀 테스트입니다.**

공개 벤치마크 문제를 복사하거나 일부 추출한 세트가 아닙니다. 모든 문항은 새로 작성한 합성 문제이며 HumanEval, LiveCodeBench, IFEval, BFCL, LongBench의 공식 점수로 보고하면 안 됩니다. 체크포인트, 양자화, 서빙 구성 변경이 대상 작업의 회귀를 일으키는지 확인하는 진단 도구입니다.

## 포함 내용

| 구분 | 문항 | 채점 |
|---|---:|---|
| Coding | 20 | Python 12 + TypeScript 4 + SQLite SQL 4; 총 166개 입출력 테스트, 입력 변경 검사 |
| Tool use | 10 | 실제 `tools` API 형식, 결정적 모의 도구 응답, 인수·순서·최종 답변 검사 |
| Reasoning | 10 | 명시된 조건에 대한 JSON 정답 검사 |
| Instruction following | 8 | 형식·단어 수·변경 지시·정형 데이터 검사 |
| Long context | 8 | 다중 증거 연결, 승인/제안 구별, 상태 추적, 근거 부재, 문서 속 지시 무시 |
| Korean | 4 | 조건 보존·사실 추출·불확실성·출력 지시 검사 |
| **합계** | **60** | **LLM 심판 없이 1차 자동 채점** |

문항 본문은 한국어 4개를 제외하고 영어입니다. 코드 문항은 작고 분명한 계약을 검증하는 단위 과제이며, Kotlin/Spring 전체 애플리케이션이나 SWE-bench식 저장소 수정 시험은 포함하지 않습니다. 난도가 낮은 문항에서 두 모델이 모두 통과할 수 있습니다. 이 경우 동등성이 입증된 것이 아니라 이 세트가 차이를 발견하지 못한 것입니다.

`tasks/core60.jsonl`에는 60개 실제 메시지가 들어 있습니다. 장문 8개는 배포 파일에서 **미측정 preview 길이**로 들어 있고, `prepare`가 실제 서빙 tokenizer로 길이를 맞춘 다음 내용을 동결합니다. preview를 200K 실험인 것처럼 보고하지 못하도록 실행기가 막습니다.

공개 저장소에는 프롬프트뿐 아니라 `tasks/oracles.json`, `SCORING.md`, 기준 구현도 포함됩니다. 이 자료를 모델에 보내면 안 되지만 누구나 읽을 수 있으므로, 이 세트는 blind·held-out 평가나 contamination-free 인증에 사용할 수 없습니다.

## 파일 위치

```text
PROMPTS.md                    60문항 읽기용 목록과 프롬프트
PROTOCOL.md                   비교 조건, 예산, 순서, 해석 규칙
SCORING.md                    채점 규칙과 문항별 정답/테스트 개요
AGENTS.md                     Codex 등 작업 에이전트용 실행 지침
VALIDATION.md                 이 패키지 자체의 검증 범위와 미검증 범위
tasks/core60.jsonl             모델에 보낼 메시지와 공개 계약
tasks/oracles.json             정답, 코드 테스트, 모의 도구 상태 (모델에 보내지 말 것)
reference_solutions/           20개 기준 구현 (모델에 보내지 말 것)
qbench/                       표준 라이브러리 기반 실행기·채점기·비교기
schemas/                      task / oracle / result JSON Schema
configs/*.example.json        로컬 endpoint 설정 예시
sandbox/                      코드 격리용 Dockerfile와 실행 wrapper
tests/                        패키지 자체 테스트
```

## GLM-5.3 Flash 측정 결과

공개용 GLM-5.3 Flash 품질·처리량 집계 결과는 [`results/glm53/REPORT.md`](results/glm53/REPORT.md)에 있습니다. 실험 시점의 장비·클럭·서빙 설정은 [`results/glm53/environment.json`](results/glm53/environment.json)에 구조화해 기록했습니다. 문항별 pass/fail과 지연, 대응 비교, domain별 처리량은 같은 디렉터리의 CSV/JSON 자료를 참고하십시오. 공개 전용으로 정리되어 원시 모델 응답과 endpoint·컨테이너·호스트 식별자는 포함하지 않습니다.

## 실험 장비와 구성

측정은 2026-10-02 기준 두 대의 DGX Spark를 묶은 분산 추론 구성에서 수행했습니다. 각 장비는 GB10 Grace Blackwell Superchip, 20-core Arm CPU(10 Cortex-X925 + 10 Cortex-A725), 128 GB LPDDR5x coherent unified memory, ConnectX-7 200 Gbps NIC 사양입니다. 제품 사양은 [NVIDIA DGX Spark Hardware Overview](https://docs.nvidia.com/dgx/dgx-spark/hardware.html)를 참고하십시오. 측정 당시 두 노드의 RoCE 링크가 활성 상태였고, GPU 전력 효율 계산에는 양쪽 GPU 전력 표본을 사용했습니다.

| 측정 환경 항목 | 기록값 | 범위와 기준일 |
|---|---|---|
| 장비 | 2 × NVIDIA DGX Spark / GB10 | 분산 추론 노드 2대; 공식 제품 사양 링크 참조 |
| CPU·메모리 | 20-core Arm, 128 GB unified memory / 노드 | 10× Cortex-X925 + 10× Cortex-A725; LPDDR5x |
| 인터커넥트 | ConnectX-7 200 Gbps, RoCE | 2026-10-02 양 노드 측정에서 GPU 전력/서버 작업 확인 |
| 호스트 OS | Ubuntu 24.04.4 LTS, ARM64 | README 작성 시 주 작업 노드에서 읽은 값 |
| GPU 소프트웨어 | NVIDIA Driver 580.173.02, CUDA 13.0 | 2026-10-02 양 노드 GPU 스냅샷에서 동일 |
| qbench 측정 클라이언트 | Python 3.12.3 | GLM 품질 실행 manifest 기록 |

### 측정한 모델과 서빙 설정

| 실험 구성 | 모델·런타임 | 주요 설정 | 측정 범위 |
|---|---|---|---|
| Qwen 기준 실행 | Qwen3.8-Flash-Next hibrid48, vLLM 0.30.0 | MTP5, BF16 KV, context 262,144; 보관된 비교 manifest의 `max_num_seqs=64` | 품질 baseline 및 과거 C1/C2/C4/C8 처리량 기준 |
| Qwen 복원 구성 | 같은 Qwen3.8-Flash-Next, vLLM 0.30.0 | MTP5, BF16 KV, context 262,144; 2026-10-02 복원 handoff 기록의 `max_num_seqs=8` | 측정 후 복원한 serving 구성; 보관된 C1–C8 처리량 기준과 구별 |
| GLM 기본 q4 | GLM-5.3-Flash-EXL3-TR3-4bpw, TensorFold v0.5.0 | dense q4, FP8 KV, checkpoint 내장 MTP, server parallelism 1, context 1,048,576 | 품질 Core52·장문, C1–C8 고정 출력 처리량 |
| GLM TensorFold v1.3.2 dense A/B | 같은 GLM checkpoint, TensorFold v0.6.0 | dense q4 또는 FP8, FP8 KV, DFlash2 drafter, server parallelism 4, context 1,048,576 | 품질 Core52·장문, 처리량 C1/C2/C3/C4 |
| GLM DFlash2 Parallel-8 | 같은 GLM checkpoint, TensorFold v0.6.0 patched Parallel 8 | dense q4, FP8 KV, DFlash2 drafter, server parallelism 8, context 262,144 | 품질은 client concurrency 1; 처리량은 client C1/C2/C4/C8 |

GLM 주 checkpoint revision은 `9eaebb7c4e96d983dcd538e18624622ba5b820a8`이며, DFlash2 실행에서 사용한 drafter revision은 `bf582e4eacc1810f76656d1811693ff6c6737d2a`입니다. 모델 가중치는 이 저장소에 포함하지 않습니다. GLM 각 구성의 점수와 처리량은 [결과 보고서](results/glm53/REPORT.md)와 그 옆의 CSV/JSON에 정리했습니다.

### GPU 클럭과 2000 MHz 설정 기록

2000 MHz는 모든 측정에 공통 적용된 값으로 기록하지 않았습니다. Qwen 보관 기준의 serving identity에는 `gpu_cap_mhz=2000`이 적혀 있지만, 양 노드의 `nvidia-smi` 스냅샷에서는 `Applications Clocks Setting`과 `SW Power Cap`이 모두 `Not Active`였습니다. 이 값은 기준 실행의 설정 metadata로 보존하되, 실제 활성 clock lock으로 검증된 값으로 해석하지 않습니다.

GLM dense q4/FP8 A/B 측정에서도 두 노드 모두 활성 application-clock lock이 없었고 클럭·전력 제한을 바꾸지 않았습니다. 해당 측정 스냅샷의 graphics/SM clock은 약 1,774 MHz, default application graphics clock은 2,418 MHz, 최대 graphics/SM clock은 3,003 MHz였습니다. 같은 날 Parallel-8 실행 스냅샷에서는 두 노드가 약 1,787/1,781 MHz였고, application clock lock과 software power cap은 활성화되어 있지 않았습니다. 클럭은 부하와 온도에 따라 달라지는 순간 측정값입니다.

복원 시점의 Qwen 서비스 설정(`max_num_seqs=8`)은 과거 처리량 기준(`max_num_seqs=64`)과 다릅니다. 따라서 과거 2000 MHz 설정 metadata와 C1–C8 처리량을 현재 서비스의 활성 설정이나 성능으로 일반화하지 마십시오. 양 노드의 환경·클럭 값은 실험 시점 기록이며, 별도 장비가 연결되어 있지 않을 때 공개 저장소만으로 현재 live 상태를 보증하지 않습니다.

## 1. 환경 준비

프로젝트 루트에서 실행합니다. 클라이언트 자체는 Python 3.10+ 표준 라이브러리만 사용합니다. `pip install`은 필요 없습니다. Docker는 **코드 채점**에만 필요합니다. TypeScript의 로컬 기준 구현 selftest에는 Node/tsc가 필요하며, 없으면 해당 4개 selftest만 skip됩니다. 실제 모델 코드의 TypeScript 채점은 Docker 이미지 안에서 수행합니다.

```bash
python -m qbench validate
python -m qbench selftest
python -m qbench build-sandboxes

cp configs/nvidia.example.json configs/nvidia.json
cp configs/hibrid48.example.json configs/hibrid48.json
cp configs/glm53.example.json configs/glm53.json
```

사용할 config의 `base_url`, `/v1/models`에 표시되는 `model` 이름, 실제 `server_identity`를 채우십시오. 예시 값은 모두 placeholder입니다. 네트워크 endpoint에는 HTTPS를 사용하십시오. HTTP는 `localhost`, `127.0.0.0/8`, `::1` 같은 loopback 주소에서만 허용됩니다. 인증이 필요할 때는 `VLLM_API_KEY` 환경변수를 설정하십시오. 키 값은 결과 manifest에 저장하지 않습니다.

`server_identity`는 운영자가 기록하는 메타데이터이며 자동 측정값이 아닙니다. 가중치 revision, 이미지 digest, 레시피 commit, MTP 길이, tokenizer/template, parser, structured decoding 여부를 실제 값으로 채우십시오. 실제 설정 파일은 `.gitignore` 대상입니다. 클라이언트는 endpoint의 served model 이름만 확인할 뿐, 그 이름이 가리키는 실제 가중치를 증명하지는 않습니다.

**이 프로그램은 모델을 다운로드하거나 서버를 재시작하거나 MTP·클럭·GMU를 바꾸지 않습니다.** 서버 운영자가 모델 구성을 직접 전환한 뒤 각 endpoint를 순차 측정하십시오.

Docker 이미지는 빌드 단계에서 네트워크를 사용합니다. 평가 중에는 네트워크가 꺼집니다. 태그는 변경될 수 있으므로 동일한 judge 이미지를 두 모델 채점에 재사용하십시오. 실제 이미지 ID는 `summary.json`에 남습니다.

## 2. 먼저 8문항 연결·파서 점검

NVIDIA가 실행 중일 때:

```bash
python -m qbench run --config configs/nvidia.json \
  --ids C01,C14,C20,T01,T08,R01,I01,K01 \
  --out runs/nvidia-smoke --concurrency 1 --repeats 1
python -m qbench grade --run runs/nvidia-smoke
```

현재 API에서 `tool_choice=auto`와 해당 모델의 tool parser / reasoning parser가 올바르게 작동해야 합니다. textual JSON에 도구 이름을 써 놓은 답을 native tool call 성공으로 바꾸어 주지 않습니다. 모든 tool 요청이 HTTP 400으로 실패하면 모델 품질을 해석하기 전에 서빙 설정부터 점검하십시오.

## 3. 52개 짧은 문항 품질 비교

장문을 제외한 52개 문항부터 권합니다. 기본 실행기는 장문을 제외합니다. `repeats=3`은 문항마다 3개의 독립 생성 시도이며, 최고 응답을 골라 채점하지 않습니다.

```bash
# 1) NVIDIA가 실행 중일 때
python -m qbench run --config configs/nvidia.json \
  --out runs/nvidia-core --concurrency 1 --repeats 3

# 2) NVIDIA endpoint를 내리고 hibrid48 endpoint를 올린 뒤
python -m qbench run --config configs/hibrid48.json \
  --out runs/hibrid48-core --concurrency 1 --repeats 3

# 3) 생성된 코드는 격리해 채점 (GPU가 없어도 가능)
python -m qbench grade --run runs/nvidia-core
python -m qbench grade --run runs/hibrid48-core

# 4) 비교
python -m qbench compare --a runs/nvidia-core \
  --b runs/hibrid48-core --out runs/comparison-core
```

두 endpoint가 같은 하드웨어 자원을 공유한다면 위 명령 사이에서 모델 구성을 수동으로 전환하십시오. 실행기는 두 endpoint가 동시에 살아 있다고 가정하지 않습니다. 코드 채점의 CPU/메모리 부하가 생성 지연에 섞이지 않도록 생성과 채점을 분리했습니다. 가능하면 별도 작업용 PC나 모델이 내려간 상태에서 채점하십시오.

기본 sampling은 `temperature=0.6, top_p=0.95, top_k=20, min_p=0`, Thinking ON입니다. 이는 **이 자체 벤치의 선택**이며 어느 모델 카드의 공식 평가 설정을 재현한 것이 아닙니다. 두 config에서 동일하게 유지하십시오. seed가 같아도 다른 엔진/커널의 동일 출력을 보장하지는 않습니다.

기본 출력 한도는 Coding/Reasoning 요청당 8192, 나머지 4096입니다. tool episode 전체 한도는 요청당 한도의 2배이며 최대 8턴입니다. 한도에 걸리면 실패/잘림으로 표시합니다. 확대가 필요하면 `max_output_tokens` 또는 `episode_output_budget`를 **두 config에 동일하게** 넣고 새로운 run으로 다시 실행하십시오. 실패 모델에만 예산을 더 주거나 기존 실패를 지우지 마십시오.

## 4. 장문 8개는 따로, C1에서

먼저 짧은 장문 smoke를 생성하여 파이프라인을 검사합니다. 이 단계는 모델 답변 생성이 아니라 tokenizer 호출입니다.

```bash
python -m qbench prepare --config configs/nvidia.json \
  --profile smoke --out prepared/core60-8k.jsonl

python -m qbench run --tasks prepared/core60-8k.jsonl \
  --config configs/nvidia.json --categories long_context --include-long \
  --out runs/nvidia-long-smoke --concurrency 1
```

전체 길이를 시험할 때는 NVIDIA가 실행 중인 동안 **한 번만** full fixture를 만듭니다.

```bash
python -m qbench prepare --config configs/nvidia.json \
  --profile full --out prepared/core60-full.jsonl

# NVIDIA 측정
python -m qbench run --tasks prepared/core60-full.jsonl \
  --config configs/nvidia.json --categories long_context --include-long \
  --out runs/nvidia-long --concurrency 1 --repeats 3

# 모델을 교체한 뒤, 같은 prepared 파일을 그대로 사용
python -m qbench run --tasks prepared/core60-full.jsonl \
  --config configs/hibrid48.json --categories long_context --include-long \
  --out runs/hibrid48-long --concurrency 1 --repeats 3

python -m qbench grade --run runs/nvidia-long
python -m qbench grade --run runs/hibrid48-long
python -m qbench compare --a runs/nvidia-long \
  --b runs/hibrid48-long --out runs/comparison-long
```

Full 입력 목표는 8192 / 16384 / 32768 / 49152 / 65536 / 98304 / 131072 / 200000토큰입니다. 맞춤 오차는 최대 약 2% 또는 128토큰입니다. 정확한 실측값은 prepare manifest에 기록합니다. 문서상 최대 context가 아니라 **메시지 입력 + 출력 예산**이 한도에 들어가도록 검사합니다. 글자 수로 토큰 수를 추정하지 않습니다.

두 번째 모델의 `/tokenize` 결과도 재확인합니다. tokenizer/template token ID가 다르면 기록하고 경고하며, 입력 텍스트는 동일하게 유지합니다. `/tokenize`가 현재 커스텀 이미지의 메시지 형식이나 kwargs를 지원하지 않으면 명시적으로 실패합니다. 조용히 길이를 줄이거나 문자 수를 토큰 수로 대체하지 않습니다. 모델의 tokenizer나 템플릿 변경 여부는 결과 해석에 포함해야 합니다.

장문을 `C2/C4`로 병렬 생성하는 것은 이 실행기에서 의도적으로 막았습니다. 이 단계는 장문 정답 회귀 시험이지 최악 조건의 OOM 스트레스 시험이 아닙니다.

## 5. 결과 읽기

```text
runs/<label>/manifest.json       설정·문항·정답 fingerprint, tokenizer 확인
runs/<label>/results.jsonl       답변, 종료 이유, 토큰 사용량, API 시간, 도구 trace
runs/<label>/raw/*.json          요청 본문과 원본 API 응답 (민감해질 수 있으므로 공유 전 확인)
runs/<label>/graded.jsonl        문항별 채점 결과
runs/<label>/SUMMARY.md          영역별 pass와 운영 완료율
runs/comparison-*/COMPARISON.md  A만 통과/B만 통과/동시 통과/동시 실패
runs/comparison-*/pairs.csv      대응 문항별 품질·지연 비교
```

`pass_rate`는 채점 가능한 시도의 통과율입니다. HTTP 장애나 judge 인프라 오류는 모델 오답과 구분하되, `operational_success_rate`에서는 성공으로 세지 않습니다. Docker가 없다는 이유로 코딩 점수를 0점으로 매기지 않습니다.

우선 **A만 통과한 문항**을 봅니다. 그 실패가 재현되는지, 도구 호출 오류가 모델 판단인지 parser 설정 문제인지 확인합니다. 지연은 두 모델이 모두 통과한 대응 문항끼리 비교합니다. 빠른 오답을 빠른 작업 완료로 세면 안 됩니다.

전체 평균 단일 점수나 “자동 채택” 판정은 만들지 않습니다. 코딩 20문항에서는 한 문항 차이가 5%p입니다. 이런 작은 세트에서 미세한 양자화 손실을 배제할 수 없습니다. 문항 단위 bootstrap은 참고 통계일 뿐, 이 수작업 합성 문제들이 실제 업무 분포를 대표한다는 근거가 아닙니다.

## 6. 중단·재개 및 blind review

```bash
# 같은 설정/같은 결과 폴더일 때만 재개. 이미 기록된 실패도 건너뛰며 지우지 않습니다.
python -m qbench run --config configs/nvidia.json \
  --out runs/nvidia-core --concurrency 1 --repeats 3 --resume

python -m qbench blind --a runs/nvidia-core \
  --b runs/hibrid48-core --out runs/blind --limit 20
```

`blind_cards.json`에는 출력 1/2와 빈 판정란이, `DO_NOT_SHARE_answer_key.json`에는 대응 관계가 있습니다. 정답 키는 판정자에게 먼저 보여주지 마십시오. LLM 심판 호출은 자동으로 하지 않습니다.

## 안전·한계

모델 생성 코드는 Docker에서만 실행합니다. host 실행으로 fallback하지 않습니다. 네트워크 없음, non-root, 읽기 전용 root/bind mount, 자원 제한, capability 제거, no-new-privileges를 적용합니다. 기대 정답은 컨테이너에 넣지 않습니다. **Docker는 완전한 보안 경계가 아니므로 신뢰할 수 없는 모델 코드에는 별도 폐기 가능한 VM/호스트와 rootless Docker를 권합니다.** 민감한 파일·자격증명·Docker socket·GPU는 judge 컨테이너에 전달하지 않습니다.

포함된 검증 기록은 기준 구현 20개와 166개 케이스, 채점 로직, HTTP 모의 서버, 재개·비교·장문 입력 준비를 다룹니다. 실제 endpoint 호환성, Docker 데몬의 격리, GPU 메모리와 장시간 안정성은 사용 환경에서 별도로 확인해야 합니다. 자세한 범위는 `VALIDATION.md`를 참고하십시오.
