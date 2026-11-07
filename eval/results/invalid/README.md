These two result files are INVALID and excluded from reporting: the model server hit
`CUDA error: out of memory` during the dense_rag run (case 18 of 77) and every later request
(including the whole raw run) returned HTTP 500. The runner at that time did not count failed calls
separately, so their latency/proxy numbers are meaningless. Kept only as a record of the incident.
Fix: model_server/server.py now empties the CUDA cache after each request, returns 503 on OOM and
marks the server unhealthy if the CUDA context breaks; the runner now records model_call_failures.
