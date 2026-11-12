| method | status | rank gain | E1 rot MAE | E1 trans MAE | E1 rot p95 | E1 false-loop excess | E2 rot MAE | E2 trans MAE | E2 rot p95 | E2 false-loop excess |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hybrid_local_loops | scored | +0.688 | 0.6131 | 0.0383 | 2.3924 | 0.0000 | 1.5726 | 0.2874 | 27.3647 | 0.0000 |
| exhaustive_two_stage | scored | +0.027 | 0.6521 | 0.0542 | 2.4276 | 0.0000 | 3.1911 | 0.4463 | 69.8079 | 0.0000 |
| gelslam_online | scored | +0.000 | 0.6557 | 0.0547 | 2.4420 | 0.0000 | 3.3417 | 0.4855 | 69.8079 | 0.0000 |
| only_nf_exhaustive | scored | -2.017 | 0.6166 | 0.0364 | 2.3738 | 0.0000 | 17.2426 | 3.0133 | 90.0000 | 0.0000 |
| nf_kf | scored | -2.453 | 0.8544 | 0.0899 | 3.5112 | 0.0000 | 17.2623 | 3.0304 | 90.0000 | 0.0000 |
| normalflow | scored | -5.218 | 3.0713 | 0.6204 | 14.3456 | 0.0000 | 7.1504 | 2.1079 | 37.1811 | 0.0000 |
| session_chain_dense | failed (train_rock_contact_loss: timed out after 900 s) | -172.012 | 90.0000 | 30.0000 | 90.0000 | 0.9800 | 90.0000 | 30.0000 | 90.0000 | 0.9800 |

Paired per-episode differences vs reference (negative = better): mean ± SE, better/worse episodes
- hybrid_local_loops: long_-rot -0.0426±0.0292 (2/0); long_-tra -0.0164±0.0113 (2/0); reloc-rot -1.7691±1.5304 (3/0); reloc-tra -0.1981±0.1430 (2/1)
- exhaustive_two_stage: long_-rot -0.0036±0.0019 (3/0); long_-tra -0.0005±0.0002 (3/0); reloc-rot -0.1506±0.1384 (2/1); reloc-tra -0.0391±0.0382 (3/0)
- only_nf_exhaustive: long_-rot -0.0392±0.0261 (4/0); long_-tra -0.0183±0.0125 (4/0); reloc-rot +13.9009±3.3411 (0/4); reloc-tra +2.5279±0.5244 (0/4)
- nf_kf: long_-rot +0.1987±0.0977 (1/3); long_-tra +0.0352±0.0266 (1/3); reloc-rot +13.9206±3.3050 (0/4); reloc-tra +2.5450±0.5217 (0/4)
- normalflow: long_-rot +2.4155±0.5247 (0/4); long_-tra +0.5657±0.1448 (0/4); reloc-rot +3.8088±3.0974 (1/3); reloc-tra +1.6224±0.6418 (1/3)
- session_chain_dense: long_-rot +0.0399±0.1162 (1/3); long_-tra -0.0082±0.0064 (2/2); reloc-rot -2.0514±2.0657 (1/2); reloc-tra -0.2060±0.2047 (3/0)
