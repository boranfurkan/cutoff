# Morning brief: Sunday 15 November

**Deadline: 12:00 sharp on Devpost.** Aim to submit by 11:30. You can keep editing until 12:00 after submitting.

## Where things stand

| | |
|---|---|
| Final sweep (03:10) | 19 of 19 repos upgraded with tests passing; 8 of 8 silent changes caught; 53 of 58 changes cited |
| Fine-tune | Best finished run: Qwen 3.5 2B, win rate 0.84. Four more runs were launched at 02:46; see "Adaption" below for the latest |
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

Log in at https://adaptionlabs.ai/app/dashboard, open the best run's page (AutoScientist column → View), and copy the "Training model name" exactly. I could not read it for you: Chrome was signed out of Adaption overnight.

By the naming pattern, the 0.84 run should be `adaption_qwen3_5_2b_adaption_train_v2_e549b6ad`. Check it against the page before pasting.

While you're on that page, note what the "Code Win Rates" chart shows. It may be the figure the leaderboard uses.

<!-- RESULTS: overnight runs are appended below -->

## If something breaks

- **The demo run fails:** rerun it; the agent is not deterministic. The existing pull request (https://github.com/boranfurkan/cutoff-demo-orders-api/pull/1) and report (`runs/1114-223529-9a42/report.html`) can stand in.
- **Databricks is slow or over quota:** drop `CUTOFF_STORE=databricks CUTOFF_TRACE=1` from the command; it then stores results locally.
- **Out of Anthropic credit:** about $11 was left at 03:15. Each demo run costs about $0.10.
- **Out of time:** the video and the Devpost submission come first. Figma and the Adaption field are optional extras.
