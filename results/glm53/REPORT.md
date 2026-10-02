# GLM-5.3 Flash 측정 결과

측정 일자: 2026-10-02 (Asia/Seoul)

이 디렉터리는 GLM-5.3 Flash의 공개용 집계 결과입니다. 원시 모델 답변, 프롬프트/응답 payload, API 설정, 로컬 경로, 컨테이너 ID와 호스트별 식별자는 포함하지 않습니다. 문항별 통과 여부와 응답 시간은 `quality_attempts.csv`, 집계 수치는 `quality_summary.json`에서 확인할 수 있습니다.

## 품질 평가

Core52는 공개 Core60 세트에서 장문 8개를 뺀 52문항이며, 각 문항을 3회 실행했습니다. 장문 평가는 8개 입력을 각각 3회 실행했습니다. 따라서 영역별 시도 수는 문항 수의 3배입니다.

| 구성 | Coding | Instruction | Korean | Reasoning | Tool | Long context |
|---|---:|---:|---:|---:|---:|---:|
| GLM Flash / TensorFold v0.5 dense q4, built-in MTP (P1) | 57/60 (95.0%) | 23/24 (95.8%) | 9/12 (75.0%) | 28/30 (93.3%) | 30/30 (100%) | 22/24 (91.7%) |
| GLM Flash / TensorFold v1.3.2 dense q4 + DFlash2 (P4) | 57/60 (95.0%) | 23/24 (95.8%) | 9/12 (75.0%) | 28/30 (93.3%) | 30/30 (100%) | 22/24 (91.7%) |
| GLM Flash / TensorFold v1.3.2 dense FP8 + DFlash2 (P4) | 58/60 (96.7%) | 23/24 (95.8%) | 9/12 (75.0%) | 28/30 (93.3%) | 30/30 (100%) | 23/24 (95.8%) |
| GLM Flash / dense q4 + DFlash2 (server P8) | 57/60 (95.0%) | 23/24 (95.8%) | 9/12 (75.0%) | 28/30 (93.3%) | 30/30 (100%) | 22/24 (91.7%) |

DFlash2 구성의 별도 8문항 smoke run도 8/8 통과했습니다. Smoke는 연결과 기본 동작을 확인하는 작은 표본이며 품질 점수 비교에는 합산하지 않았습니다. 모든 qbench 품질 실행의 client concurrency는 1이었습니다. server parallelism 8 구성은 별도 처리량 sweep에서 client concurrency C1/C2/C4/C8을 측정했습니다.

### 대응 비교

| 비교 | Coding | Instruction | Korean | Reasoning | Tool | Long context |
|---|---:|---:|---:|---:|---:|---:|
| GLM Flash dense q4 − 보관된 Qwen3.8 Cluster 기준 | +35.0 pp | −4.2 pp | −25.0 pp | −6.7 pp | 0 pp | 0 pp |
| GLM Flash DFlash2 구성 − 보관된 Qwen3.8 Cluster 기준 | +35.0 pp | −4.2 pp | −25.0 pp | −6.7 pp | 0 pp | 0 pp |
| GLM Flash dense FP8 − dense q4 | +1.7 pp | 0 pp | 0 pp | 0 pp | 0 pp | +4.2 pp |

비교는 공개된 합성 문항의 대응 시도에 한정됩니다. q4와 FP8 비교의 task-cluster bootstrap 95% 구간은 차이가 없을 가능성을 포함합니다. 이 결과는 전반적인 모델 우열이나 양자화 동등성을 증명하지 않습니다. Qwen 비교는 모델·실행기·서빙 구성이 다른 보관 기준 결과이므로 GLM 체크포인트나 커널 차이만의 효과로 해석할 수 없습니다. 비교별 시도 수, 통과 문항 수, 신뢰 구간은 `quality_comparisons.csv`에 있습니다.

## 처리량 및 GPU 에너지

처리량은 두 DGX Spark에서 별도 고정 프롬프트 부하 실험으로 측정한 completion tokens/s입니다. 아래 GLM 대 Qwen 수치는 네 prompt domain을 합친 기존 보관 결과입니다. Qwen은 과거 서빙 구성의 기준선이며 현재 같은 설정을 재측정한 값이 아닙니다.

| Client concurrency | GLM Flash tok/s | Qwen 기준 tok/s | GLM GPU tok/J | Qwen 기준 GPU tok/J |
|---:|---:|---:|---:|---:|
| 1 | 53.11 | 53.32 | 1.090 | 1.632 |
| 2 | 53.10 | 82.42 | 1.078 | 2.369 |
| 4 | 53.10 | 122.25 | 1.069 | 3.365 |
| 8 | 53.10 | 181.79 | 1.065 | 4.546 |

해당 GLM 기본 구성은 server parallelism 1이어서 client 동시성을 높여도 총 처리량이 약 53 tok/s로 유지됐습니다. C1에서는 처리량이 비슷했지만 GPU 에너지당 토큰은 GLM 쪽이 낮았고, C8에서는 Qwen 보관 기준의 처리량이 더 높았습니다. Qwen과 모델·런타임 설정이 다른 운영 비교입니다.

### GLM q4 + DFlash2, server parallelism 8

별도 측정은 TensorFold v0.6.0의 server parallelism 8 구성과 262,144-token context에서 수행했습니다. 각 domain/load 조합에서 256-token warmup 뒤 2,048 completion-token 요청 3회를 측정했습니다. 아래 pooled 값은 생성 토큰 수와 측정 GPU energy를 기준으로 네 domain을 합친 결과입니다.

| Client concurrency | Output tok/s | GPU tok/J |
|---:|---:|---:|
| 1 | 49.9 | 1.06 |
| 2 | 91.2 | 1.89 |
| 4 | 162.2 | 3.29 |
| 8 | 244.8 | 4.89 |

Domain별 값은 `throughput.csv`에 있습니다. tok/s에는 reasoning token이 포함됩니다. GPU energy는 두 기기의 GPU 전력만 적분했고 host/system energy와 idle draw를 제외했습니다.

TensorFold v1.3.2 dense q4와 FP8의 C1–C4 비교에서는 FP8이 영어·한국어·중국어 prose에서 q4보다 느렸고, coding에서는 2.6–21.7% 빨랐습니다. 자세한 domain/load별 output·input 처리량 및 GPU tok/J 수치는 `throughput.csv`에 있습니다. CSV의 에너지 효율 변화율은 보고서에 표시된 tok/J 반올림 수치에서 계산했습니다. GPU 에너지는 두 장치의 GPU 전력만 포함하며 host 전력과 idle draw를 제외합니다. cached input 비율은 backend가 제공한 진단치로, 다른 실행기 간 보정된 cache 비교값으로 볼 수 없습니다.

## 장문 입력 tokenization

같은 고정 텍스트를 사용했지만 Qwen 준비 단계와 GLM tokenizer가 세는 토큰 수는 다릅니다. L01–L08의 양쪽 입력 토큰 수는 `long_context_tokens.csv`에 있습니다. 따라서 이 장문 결과는 같은 텍스트 입력에 대한 실행 비교이지 모델 간 같은 토큰 길이의 비교가 아닙니다.

## 실행 식별 및 재현 범위

- 기본 GLM 실행은 GLM-5.3-Flash-EXL3-TR3-4bpw 체크포인트, TensorFold v0.5.0과 dense q4 구성입니다. 기본 체크포인트 revision은 `9eaebb7c4e96d983dcd538e18624622ba5b820a8`입니다.
- q4/FP8 A/B는 같은 체크포인트에 TensorFold v1.3.2/v0.6.0을 적용했습니다. q4/FP8 A/B의 DFlash2 drafter revision은 `bf582e4eacc1810f76656d1811693ff6c6737d2a`였고 server parallelism은 4, context는 1,048,576 tokens였습니다. 별도 Parallel-8 실행은 dense q4 + DFlash2, server parallelism 8, context 262,144 tokens였습니다.
- 품질 실행은 Core52와 장문 입력을 각각 별도 실행했습니다. qbench 점수는 deterministic oracle로 채점했으며 LLM 심판 점수는 아닙니다.
- 이 벤치마크의 문항, 기준 답안, 채점 규칙은 공개되어 있습니다. 따라서 이 기록은 회귀 진단용이지 blind/held-out 평가나 contamination-free 인증이 아닙니다.
- `quality_attempts.csv`에는 문항 ID, 반복 번호, 상태, pass/fail, 응답 시간과 토큰 계수만 있습니다. 모델 응답 텍스트와 오류 본문은 공개 결과에서 제외했습니다.
