# Morning brief: Sunday 15 November

**Deadline: 12:00 sharp on Devpost.** Aim to submit by 11:30. You can keep editing until 12:00 after submitting.

## Where things stand

| | |
|---|---|
| Final sweep (03:10) | 19 of 19 repos upgraded with tests passing; 8 of 8 silent changes caught; 53 of 58 changes cited |
| Fine-tune | All nine runs finished. Model used in the product: Qwen 3.5 2B, win rate 0.84. Two overnight runs scored higher on Adaption (0.89 and 1.0); see "Adaption" below before choosing the model ID |
| Devpost | Draft at 3 of 5 steps. Story, tags, repo link, track, bounties, team line, banner and screenshot are saved |
| Figma | Six frames, a colour-variable collection, six text styles, seven components. No auto layout or prototype link |
| GitHub | Everything pushed to https://github.com/boranfurkan/cutoff |

## Your steps, in order

### 1. Record the video (30–45 min)
The script is in `docs/SUBMISSION.md` under "Video script". Maximum 2:00; Devpost cuts it off there.

Before recording:
- Start Docker Desktop and wait until it says it's running.
- Close heavy apps. Do **not** use the local fine-tuned model during the recording; it needs most of the machine's memory.
- Use a large terminal font.

The command to record (it opens a new pull request on the demo repo each time):

```bash
cd ~/Desktop/cutoff
CUTOFF_STORE=databricks CUTOFF_TRACE=1 .venv/bin/python -m cutoff.cli run boranfurkan/cutoff-demo-orders-api --pr
```

It takes about 45 seconds and costs about $0.10. Do one dry run first. It prints the pull-request link and the path of the report page; open both for the second half of the video.

Things to show after the run, in this order:
1. The pull request on GitHub.
2. The report page (`runs/<id>/report.html`).
3. Databricks: the `/Shared/cutoff` experiment (Traces tab, then Evaluation runs), and the `workspace.default.cutoff_rules` table.
4. The results table in the README.
5. For the Figma and Adaption prizes: a few seconds of the Figma file, and the Adaption run page showing the win rate.

### 2. Upload the video
YouTube or Vimeo; unlisted is fine. Devpost only accepts a link from one of those.

### 3. Finish Devpost
Open https://devpost.com/submit-to/32099-imperial-ai-hackathon/manage/submissions/1304213-cutoff/project_details/edit

- **Project details:** paste the video link, save.
- **Additional info:**
  - *Figma link:* in Figma click Share, set "anyone with the link" to "can view", copy the link, paste it.
  - *Adaption model ID:* see "Adaption" below.
- **Submit:** tick the terms box and press Submit.

### 4. Ask an organiser (at the help desk)
- Is the Adaption leaderboard based on the run's win rate, and does the model ID we entered match what they expect?
- Is your student status acceptable? The rules require a current university student, and your MSc starts in February.

## Adaption

All four overnight runs finished by 04:50. Results of all nine:

| Run | Model | Training data | Adaption win rate |
|---|---|---|---|
| `99eef0cd` | Gemma 3 4B (pt) | v3 | **1.00** (stopped at iteration 3 of 5: target reached) |
| `d7b8ffb8` | Qwen 3.5 2B | v3 | **0.89** |
| `00cad367` | Qwen 3.5 2B, 6 epochs | v2 | 0.84 |
| `e549b6ad` | Qwen 3.5 2B | v2 | 0.84 (the model in the product and the README) |
| `f157cbd1` | Qwen 3 4B Base | v3 | 0.78 |
| `019b4950` | Qwen 3.5 9B | v2 | 0.68 |
| `59ffc118` | Qwen 3.5 4B | v2 | 0.67 |
| `13d1399f` | Qwen 3.5 9B | v1 | 0.62 |
| `ad1a7258` | Qwen 3.5 4B + augmentation | v2 | 0.54 |

**What I checked.** I downloaded the 0.89 model and ran it on our 30 held-out excerpts. It is worse than the 0.84 model there: it finds 44% of breaking changes (0.84 model: 47%) and, on the 8 excerpts with no breaking change, it invents one every time (0.84 model: right on 7 of 8). The v3 training set has no "nothing to report" examples, which explains it. So the 0.84 model stays in the product, and the README is unchanged.

**What I could not check.** The Gemma run's 1.00. Its base model needs a licence accepted on Hugging Face under your account, so I could not run it locally. A win rate of 1.00 is measured against untuned Gemma "pt", which is not a chat model and probably fails the task outright, so the number says less than it looks.

**Which model ID to enter (your call, ideally after asking the organiser):**
- If the leaderboard ranks by Adaption win rate, enter the Gemma run (1.00), or the 2B v3 run (0.89) if you prefer a number I verified runs.
- If judges look at the model in use, enter `e549b6ad` (0.84); it is the one the README and Devpost story describe.

Log in at https://adaptionlabs.ai/app/dashboard, open the run's page (AutoScientist column → View), and copy the "Training model name" exactly. I could not read it for you: Chrome was signed out of Adaption overnight. By the naming pattern the names should be close to these; check before pasting:
- `adaption_gemma_3_4b_pt_adaption_train_v3_99eef0cd`
- `adaption_qwen3_5_2b_adaption_train_v3_d7b8ffb8`
- `adaption_qwen3_5_2b_adaption_train_v2_e549b6ad`

While you're on that page, note what the "Code Win Rates" chart shows. It may be the figure the leaderboard uses.

If you enter a run other than `e549b6ad`, add one line to the Devpost story so it matches, for example: "Our highest Adaption win rate was 1.00 (Gemma 3 4B); the model we use in the product scored 0.84."

## If something breaks

- **The demo run fails:** rerun it; the agent is not deterministic. The existing pull request (https://github.com/boranfurkan/cutoff-demo-orders-api/pull/1) and report (`runs/1114-223529-9a42/report.html`) can stand in.
- **Databricks is slow or over quota:** drop `CUTOFF_STORE=databricks CUTOFF_TRACE=1` from the command; it then stores results locally.
- **Out of Anthropic credit:** about $11 was left at 03:15. Each demo run costs about $0.10.
- **Out of time:** the video and the Devpost submission come first. Figma and the Adaption field are optional extras.
