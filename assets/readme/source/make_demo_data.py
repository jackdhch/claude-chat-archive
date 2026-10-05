#!/usr/bin/env python3
"""生成一套全英文、全虚构的演示数据（README 截图用），格式与 tests/make_fixtures.py 一致。
用法：python3 assets/readme/source/make_demo_data.py <目标目录>
产物：<目标目录>/home/（假 HOME：.claude/projects、Downloads、desktop-meta）+ <目标目录>/config.json。
最后打印可直接运行的导出命令。确定性：同样代码同样输出。人名、路径全是编的。"""
import json, os, random, shutil, sys, zipfile
sys.dont_write_bytecode = True
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'tests'))
import make_fixtures as mf          # 复用 Sess / am / GConv 等写法；只用它的函数，不让它写 tests/fixtures
from make_fixtures import U, txt, think, tool, T_

RND = random.Random(2026)
PROJECTS = {'web': '/home/alex/web-dashboard', 'ml': '/home/alex/ml-experiments', 'dot': '/home/alex/dotfiles',
            'blog': '/home/alex/blog', 'rust': '/home/alex/rust-cli', 'infra': '/home/alex/infra'}
def L(*lines): return '\n'.join(lines)
def numbered(body): return '\n'.join(f'{i:>6}\t{l}' for i, l in enumerate(body.strip('\n').split('\n'), 1))

# ───────────── Claude Code：小语言（Q = 一个提问回合；th/tx/rd/ed/wr/sh/gr/ag = 步骤）─────────────
def th(t): return ('th', t)
def tx(t): return ('tx', t)
def rd(path, body): return ('tool', 'Read', {'file_path': path}, numbered(body), False)
def ed(path, old, new): return ('tool', 'Edit', {'file_path': path, 'old_string': old, 'new_string': new, 'replace_all': False},
                                f'The file {path} has been updated. Here\'s the result of running `cat -n` on a snippet of the edited file:\n' + numbered(new), False)
def wr(path, content): return ('tool', 'Write', {'file_path': path, 'content': content}, f'File created successfully at: {path}', False)
def sh(cmd, out, desc=None, err=False): return ('tool', 'Bash', {'command': cmd, 'description': desc or cmd.split('\n')[0][:60]}, out, err)
def gr(pat, out): return ('tool', 'Grep', {'pattern': pat, 'output_mode': 'content', '-n': True}, out, False)
def ag(desc, prompt, result, sub): return ('agent', desc, prompt, result, sub)
def Q(prompt, ans='', *steps): return (prompt, ans, steps)
def S(proj, title, *turns, compact=None): return dict(proj=proj, title=title, turns=turns, compact=compact)

SESSIONS = [
 S('web', 'Add dark mode toggle to settings page',
   Q('Add a dark mode toggle to the settings page. We already have CSS variables in theme.css, so it should just flip a data attribute.',
     'Done. The toggle lives in `SettingsPage.tsx`, writes the choice to `localStorage`, and sets `data-theme` on `<html>` so the existing variables take over. I also made it follow `prefers-color-scheme` until the user picks something explicitly.',
     th('The user wants a toggle that flips a data attribute. Check how theme.css is organised and where settings live before touching anything.'),
     rd('/home/alex/web-dashboard/src/styles/theme.css', ':root {\n  --bg: #ffffff;\n  --fg: #1a1a1a;\n  --accent: #3b5bdb;\n}\n\n[data-theme="dark"] {\n  --bg: #14151a;\n  --fg: #e8e8ec;\n  --accent: #748ffc;\n}'),
     gr('data-theme', 'src/styles/theme.css:6:[data-theme="dark"] {\nsrc/hooks/useTheme.ts:11:  document.documentElement.dataset.theme = theme;'),
     rd('/home/alex/web-dashboard/src/hooks/useTheme.ts', 'import { useEffect, useState } from "react";\n\nexport function useTheme() {\n  const [theme, setTheme] = useState<"light" | "dark">("light");\n  useEffect(() => {\n    document.documentElement.dataset.theme = theme;\n  }, [theme]);\n  return { theme, setTheme };\n}'),
     ed('/home/alex/web-dashboard/src/hooks/useTheme.ts', 'useState<"light" | "dark">("light")', 'useState<"light" | "dark">(() =>\n    (localStorage.getItem("theme") as "light" | "dark") ??\n    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"))')),
   Q('Can you add a test for it?', 'Added two tests: one checks that clicking the switch sets `data-theme="dark"`, the other that the choice survives a re-render via `localStorage`. Both pass.',
     wr('/home/alex/web-dashboard/src/hooks/useTheme.test.tsx', 'import { renderHook, act } from "@testing-library/react";\nimport { useTheme } from "./useTheme";\n\ntest("persists the chosen theme", () => {\n  const { result } = renderHook(() => useTheme());\n  act(() => result.current.setTheme("dark"));\n  expect(localStorage.getItem("theme")).toBe("dark");\n});'),
     sh('npx vitest run src/hooks', ' RUN  v1.6.0\n\n ✓ src/hooks/useTheme.test.tsx (2)\n\n Test Files  1 passed (1)\n      Tests  2 passed (2)\n   Duration  642ms'))),
 S('rust', 'Scaffold a clap-based CLI with subcommands',
   Q('I want a small CLI called `stash` with subcommands `add`, `list` and `rm`. Use clap derive.',
     'The scaffold is in place: `stash add <name> <path>`, `stash list`, and `stash rm <name>`. Each subcommand is a variant of `Command` and dispatches to its own function in `commands.rs`, which makes them easy to test separately.',
     sh('cargo new stash && cd stash && cargo add clap --features derive', '     Created binary (application) `stash` package\n      Adding clap v4.5.4 to dependencies\n             Features:\n             + derive, std, help, usage'),
     wr('/home/alex/rust-cli/src/main.rs', 'use clap::{Parser, Subcommand};\n\n#[derive(Parser)]\n#[command(version, about = "Keep track of named directories")]\nstruct Cli {\n    #[command(subcommand)]\n    command: Command,\n}\n\n#[derive(Subcommand)]\nenum Command {\n    Add { name: String, path: std::path::PathBuf },\n    List,\n    Rm { name: String },\n}\n\nfn main() {\n    let cli = Cli::parse();\n    match cli.command {\n        Command::Add { name, path } => println!("added {name} -> {}", path.display()),\n        Command::List => println!("(empty)"),\n        Command::Rm { name } => println!("removed {name}"),\n    }\n}'),
     sh('cargo run -- add notes ~/notes && cargo run -- list', '   Compiling stash v0.1.0\n    Finished dev [unoptimized + debuginfo] target(s) in 1.84s\nadded notes -> /home/alex/notes\n(empty)')),
   Q('Make `list` print a table instead, sorted by name.', 'Switched `list` to a sorted, aligned table. For now the entries are held in a `BTreeMap`, so sorting comes for free; persistence is the next step.',
     ed('/home/alex/rust-cli/src/main.rs', 'Command::List => println!("(empty)"),', 'Command::List => {\n            let width = entries.keys().map(|k| k.len()).max().unwrap_or(0);\n            for (name, path) in &entries {\n                println!("{name:<width$}  {}", path.display());\n            }\n        }'))),
 S('infra', 'Write Terraform module for S3 static hosting',
   Q('Create a reusable Terraform module for hosting a static site on S3 behind CloudFront. Inputs: bucket name, domain, price class.',
     'The module is in `modules/static-site`. It creates a private bucket, a CloudFront distribution with an origin access control, and outputs the distribution domain. The bucket is never public; only CloudFront can read it.',
     th('Keep the bucket private with OAC, not a legacy OAI. Variables: bucket_name, domain, price_class with a sane default.'),
     sh('ls modules environments', 'environments:\nstaging  production\n\nmodules:\n(empty)'),
     wr('/home/alex/infra/modules/static-site/main.tf', 'resource "aws_s3_bucket" "site" {\n  bucket = var.bucket_name\n}\n\nresource "aws_s3_bucket_public_access_block" "site" {\n  bucket                  = aws_s3_bucket.site.id\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}\n\nresource "aws_cloudfront_origin_access_control" "site" {\n  name                              = "${var.bucket_name}-oac"\n  origin_access_control_origin_type = "s3"\n  signing_behavior                  = "always"\n  signing_protocol                  = "sigv4"\n}'),
     sh('terraform -chdir=modules/static-site init -backend=false && terraform -chdir=modules/static-site validate', 'Terraform has been successfully initialized!\nSuccess! The configuration is valid.'))),
 S('dot', 'Set up zsh with fzf history search',
   Q('Wire fzf into my zsh config so Ctrl-R gives fuzzy history search with a preview.',
     'Ctrl-R now opens fzf over the deduplicated history, with the full command shown in a preview pane. I put it in `zsh/fzf.zsh` and sourced it from `.zshrc` only when fzf is installed, so a fresh machine without it will not error out.',
     rd('/home/alex/dotfiles/zsh/.zshrc', 'export EDITOR=nvim\nsetopt HIST_IGNORE_ALL_DUPS SHARE_HISTORY\nHISTSIZE=50000\nSAVEHIST=50000\n\nfor f in ~/.config/zsh/*.zsh; do source "$f"; done'),
     wr('/home/alex/dotfiles/zsh/fzf.zsh', 'if command -v fzf >/dev/null; then\n  source <(fzf --zsh)\n  export FZF_CTRL_R_OPTS="--preview \'echo {}\' --preview-window down:3:wrap --bind ctrl-/:toggle-preview"\nfi'),
     sh('zsh -ic \'bindkey | grep fzf-history\'', '"^R" fzf-history-widget'))),
 S('blog', 'Draft post on Rust error handling',
   Q('Help me outline a blog post comparing `anyhow` and `thiserror`. Target audience: people who just finished the Rust book.',
     'Here is an outline that builds from the problem to the rule of thumb:\n\n1. Why `Box<dyn Error>` stops being enough\n2. `thiserror` for libraries: typed errors callers can match on\n3. `anyhow` for applications: context without ceremony\n4. A small example using both in one crate\n5. Rule of thumb: libraries define errors, binaries report them\n\nI saved it as a draft with the example project listed in the front matter.',
     wr('/home/alex/blog/content/drafts/rust-error-handling.md', '---\ntitle: "anyhow vs thiserror"\ndraft: true\ntags: [rust]\n---\n\n## Why Box<dyn Error> stops being enough\n\n## thiserror for libraries\n\n## anyhow for applications\n\n## Using both in one crate\n\n## Rule of thumb')),
   Q('Write the section about `thiserror` with a short example.', 'Added the section. The example defines a `ConfigError` with two variants and shows the caller matching on one of them, which is the point of using a typed error.',
     ed('/home/alex/blog/content/drafts/rust-error-handling.md', '## thiserror for libraries', '## thiserror for libraries\n\n```rust\n#[derive(Debug, thiserror::Error)]\npub enum ConfigError {\n    #[error("could not read {path}")]\n    Io { path: String, #[source] source: std::io::Error },\n    #[error("invalid value for `{0}`")]\n    Invalid(String),\n}\n```\n\nCallers can now `match` on `ConfigError::Invalid` and recover.'))),
 S('ml', 'Reproduce baseline ResNet accuracy',
   Q('Our ResNet-18 baseline on CIFAR-10 should reach about 93% but I only get 89%. Can you find out why?',
     'Found two causes. The training loop applied `RandomCrop` after `Normalize`, which pads with the normalized value of zero instead of black, and the weight decay was set on the batch-norm parameters as well. After fixing both, validation accuracy goes to 93.1% over 3 seeds (mean).',
     th('89 vs 93 is a classic augmentation or optimizer detail. Look at the transforms and the optimizer groups first.'),
     rd('/home/alex/ml-experiments/train.py', 'tf = transforms.Compose([\n    transforms.ToTensor(),\n    transforms.Normalize(MEAN, STD),\n    transforms.RandomCrop(32, padding=4),\n    transforms.RandomHorizontalFlip(),\n])\nopt = torch.optim.SGD(model.parameters(), lr=0.1, momentum=0.9, weight_decay=5e-4)'),
     ed('/home/alex/ml-experiments/train.py', '    transforms.ToTensor(),\n    transforms.Normalize(MEAN, STD),\n    transforms.RandomCrop(32, padding=4),\n    transforms.RandomHorizontalFlip(),', '    transforms.RandomCrop(32, padding=4),\n    transforms.RandomHorizontalFlip(),\n    transforms.ToTensor(),\n    transforms.Normalize(MEAN, STD),'),
     sh('python train.py --epochs 30 --seed 0 2>&1 | tail -3', 'epoch 28  train_loss 0.041  val_acc 0.9287\nepoch 29  train_loss 0.039  val_acc 0.9301\nepoch 30  train_loss 0.038  val_acc 0.9312'))),
 S('web', 'Fix flaky integration test in CI',
   Q('The `checkout.spec.ts` integration test fails about one run in five on CI but never locally. Please find the cause.',
     'The test clicked "Place order" before the cart request had resolved, so it sometimes read an empty cart. Locally the API answers in a few milliseconds, on CI it takes longer. I replaced the fixed `waitForTimeout(500)` with waiting on the `/api/cart` response and the button becoming enabled. I ran it 30 times in a loop with no failures.',
     th('Flaky only on CI usually means a race. Look for sleeps or missing awaits in the spec.'),
     rd('/home/alex/web-dashboard/tests/checkout.spec.ts', 'test("places an order", async ({ page }) => {\n  await page.goto("/cart");\n  await page.waitForTimeout(500);\n  await page.click("text=Place order");\n  await expect(page.locator(".confirmation")).toBeVisible();\n});'),
     ed('/home/alex/web-dashboard/tests/checkout.spec.ts', '  await page.waitForTimeout(500);\n  await page.click("text=Place order");', '  await page.waitForResponse((r) => r.url().includes("/api/cart") && r.ok());\n  const button = page.getByRole("button", { name: "Place order" });\n  await expect(button).toBeEnabled();\n  await button.click();'),
     sh('for i in $(seq 30); do npx playwright test checkout.spec.ts --reporter=dot || break; done', 'Running 1 test using 1 worker\n  1 passed (2.1s)\n... (30 runs)\nAll 30 runs passed')),
   Q('Is the same pattern in other specs?', 'Yes, four more specs use fixed sleeps. I listed them but did not change them yet:\n\n- `tests/profile.spec.ts:14`\n- `tests/search.spec.ts:9`\n- `tests/search.spec.ts:31`\n- `tests/orders.spec.ts:22`\n\nWant me to convert those too?',
     gr('waitForTimeout', 'tests/profile.spec.ts:14:  await page.waitForTimeout(300);\ntests/search.spec.ts:9:  await page.waitForTimeout(1000);\ntests/search.spec.ts:31:  await page.waitForTimeout(250);\ntests/orders.spec.ts:22:  await page.waitForTimeout(500);'))),
 S('web', 'Paginate the orders table',
   Q('The orders table loads everything at once and is slow with 10k rows. Add server-side pagination. Check how the API is structured first, use a subagent if it helps.',
     'Pagination is in. The API now accepts `?page=` and `?pageSize=` (default 25, max 100) and returns `{ items, total }`; the table shows page controls and keeps the page in the URL so reload and back-button work.',
     ag('Map orders API', 'Find how the orders endpoint is implemented and what the frontend calls it with. Report file paths and the query shape.',
        'The route is `server/routes/orders.ts` (GET /api/orders, no limit). The table calls it through `useOrders()` in `src/hooks/useOrders.ts`.',
        [rd('/home/alex/web-dashboard/server/routes/orders.ts', 'router.get("/orders", async (req, res) => {\n  const rows = await db.select().from(orders).orderBy(desc(orders.createdAt));\n  res.json(rows);\n});'),
         gr('useOrders', 'src/hooks/useOrders.ts:4:export function useOrders() {\nsrc/components/OrdersTable.tsx:9:  const { data } = useOrders();')]),
     ed('/home/alex/web-dashboard/server/routes/orders.ts', '  const rows = await db.select().from(orders).orderBy(desc(orders.createdAt));\n  res.json(rows);', '  const page = Math.max(1, Number(req.query.page) || 1);\n  const pageSize = Math.min(100, Number(req.query.pageSize) || 25);\n  const [items, [{ total }]] = await Promise.all([\n    db.select().from(orders).orderBy(desc(orders.createdAt)).limit(pageSize).offset((page - 1) * pageSize),\n    db.select({ total: count() }).from(orders),\n  ]);\n  res.json({ items, total });'),
     sh('npx vitest run server/routes', ' ✓ server/routes/orders.test.ts (4)\n\n Test Files  1 passed (1)\n      Tests  4 passed (4)'))),
 S('infra', 'Rotate Docker base image to distroless',
   Q('Switch the API image from node:20 to a distroless base. Keep the image small and don\'t break the healthcheck.',
     'The image is now a two-stage build ending in `gcr.io/distroless/nodejs20-debian12`. Size went from 1.1 GB to 168 MB. Distroless has no shell or curl, so I replaced the shell-based healthcheck with a tiny `healthcheck.js` that calls the `/healthz` endpoint using Node itself.',
     rd('/home/alex/infra/docker/api/Dockerfile', 'FROM node:20\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nHEALTHCHECK CMD curl -f http://localhost:3000/healthz || exit 1\nCMD ["node", "dist/server.js"]'),
     wr('/home/alex/infra/docker/api/Dockerfile', 'FROM node:20-slim AS build\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build && npm prune --omit=dev\n\nFROM gcr.io/distroless/nodejs20-debian12\nWORKDIR /app\nCOPY --from=build /app/dist ./dist\nCOPY --from=build /app/node_modules ./node_modules\nCOPY healthcheck.js ./\nHEALTHCHECK CMD ["/nodejs/bin/node", "healthcheck.js"]\nCMD ["dist/server.js"]'),
     sh('docker build -t api:distroless docker/api && docker images api:distroless', '[+] Building 41.2s (14/14) FINISHED\nREPOSITORY   TAG          IMAGE ID       SIZE\napi          distroless   3f1c9a7be2d4   168MB'))),
 S('ml', 'Add learning rate warmup scheduler',
   Q('Add a linear warmup for the first 500 steps followed by cosine decay. I use a plain PyTorch loop.',
     'Added `build_scheduler` using `LambdaLR`: linear ramp from 0 to the base learning rate over 500 steps, then cosine decay down to 1% of the base. I call `scheduler.step()` after each optimizer step, not each epoch, which is the usual mistake with this setup.',
     rd('/home/alex/ml-experiments/train.py', 'opt = torch.optim.AdamW(model.parameters(), lr=3e-4)\nfor epoch in range(args.epochs):\n    for batch in loader:\n        loss = step(model, batch)\n        opt.zero_grad(); loss.backward(); opt.step()'),
     ed('/home/alex/ml-experiments/train.py', 'opt = torch.optim.AdamW(model.parameters(), lr=3e-4)', 'opt = torch.optim.AdamW(model.parameters(), lr=3e-4)\ntotal = args.epochs * len(loader)\nscheduler = torch.optim.lr_scheduler.LambdaLR(\n    opt, lambda s: s / 500 if s < 500 else 0.01 + 0.99 * 0.5 * (1 + math.cos(math.pi * (s - 500) / (total - 500))))'),
     sh('python -c "from train import *; print(lr_curve(total=2000)[::400])"', '[0.0, 0.00024, 0.00029, 0.00018, 0.00006]')),
   Q('Log the learning rate to TensorBoard too.', 'Done: the current learning rate is now written as `lr` every 50 steps next to the loss.',
     ed('/home/alex/ml-experiments/train.py', 'opt.step()', 'opt.step(); scheduler.step()\n        if step_i % 50 == 0:\n            writer.add_scalar("lr", scheduler.get_last_lr()[0], step_i)'))),
 S('rust', 'Migrate config to TOML',
   Q('Our CLI reads `~/.stashrc` in a home-made key=value format. Move it to TOML, but keep reading the old file as a fallback with a warning.',
     'Config is now `~/.config/stash/config.toml`, parsed with `serde` and `toml`. If only the old `~/.stashrc` exists, it is parsed with the legacy reader, a deprecation warning goes to stderr, and the equivalent TOML is printed so users can copy it.',
     rd('/home/alex/rust-cli/src/config.rs', 'pub struct Config {\n    pub editor: String,\n    pub max_entries: usize,\n}\n\npub fn load() -> Config {\n    let text = std::fs::read_to_string(home().join(".stashrc")).unwrap_or_default();\n    parse_legacy(&text)\n}'),
     sh('cargo add serde --features derive && cargo add toml', '      Adding serde v1.0.203 to dependencies\n      Adding toml v0.8.14 to dependencies'),
     ed('/home/alex/rust-cli/src/config.rs', 'pub fn load() -> Config {', '#[derive(serde::Deserialize, serde::Serialize)]\npub struct Config {\n    pub editor: String,\n    pub max_entries: usize,\n}\n\npub fn load() -> Config {\n    if let Ok(text) = std::fs::read_to_string(config_path()) {\n        return toml::from_str(&text).expect("invalid config.toml");\n    }'),
     sh('cargo test config', 'running 3 tests\ntest config::tests::reads_toml ... ok\ntest config::tests::falls_back_to_legacy ... ok\ntest config::tests::defaults_when_missing ... ok\n\ntest result: ok. 3 passed')),
   Q('Add a `stash config --migrate` command that writes the new file.', 'Added. It refuses to overwrite an existing `config.toml` unless you pass `--force`, and it leaves the old file in place.')),
 S('rust', 'Add --json output flag',
   Q('Add a global `--json` flag so `list` prints machine-readable output.', 'Added a global `--json` flag. `stash list --json` now prints an array of `{ "name", "path" }` objects; the table output is unchanged without it. I used `serde_json::to_writer_pretty` on stdout.',
     ed('/home/alex/rust-cli/src/main.rs', 'struct Cli {', 'struct Cli {\n    /// Print machine-readable JSON\n    #[arg(long, global = true)]\n    json: bool,\n'),
     sh('cargo run -q -- list --json', '[\n  {\n    "name": "notes",\n    "path": "/home/alex/notes"\n  }\n]'))),
 S('dot', 'Fix tmux colors over SSH',
   Q('Colors in Neovim look washed out inside tmux when I SSH into my dev box. True color works locally.',
     'The remote tmux did not know the outer terminal supports true color. Two lines fix it: tell tmux to advertise RGB for `xterm-256color`, and set `COLORTERM=truecolor` in the SSH session. Reload with `tmux source-file ~/.tmux.conf` and restart Neovim.',
     rd('/home/alex/dotfiles/tmux/.tmux.conf', 'set -g default-terminal "screen-256color"\nset -g mouse on\nset -g history-limit 50000'),
     ed('/home/alex/dotfiles/tmux/.tmux.conf', 'set -g default-terminal "screen-256color"', 'set -g default-terminal "tmux-256color"\nset -as terminal-features ",xterm-256color:RGB"'),
     sh('tmux info | grep -i rgb', '203: RGB: (flag) true'))),
 S('blog', 'Add RSS feed to static site',
   Q('The blog is built with a tiny Node script. Add an RSS 2.0 feed with the 20 latest posts.', 'The build now writes `public/feed.xml` with the 20 newest non-draft posts, absolute URLs and RFC 822 dates. I also added the `<link rel="alternate">` tag to the layout so feed readers discover it.',
     rd('/home/alex/blog/build.mjs', 'const posts = await loadPosts("content/posts");\nfor (const p of posts) await writePage(p);\nawait writeIndex(posts);'),
     ed('/home/alex/blog/build.mjs', 'await writeIndex(posts);', 'await writeIndex(posts);\nawait writeFeed(posts.filter((p) => !p.draft).slice(0, 20));'),
     sh('node build.mjs && xmllint --noout public/feed.xml && echo valid', 'Built 38 pages\nvalid'))),
 S('web', 'Debounce search input',
   Q('Typing in the global search box fires a request per keystroke. Debounce it by 250 ms and cancel stale requests.', 'The search hook now waits 250 ms after the last keystroke and aborts the previous request with an `AbortController`, so slow responses can no longer overwrite newer results.',
     rd('/home/alex/web-dashboard/src/hooks/useSearch.ts', 'export function useSearch(query: string) {\n  const [results, setResults] = useState<Result[]>([]);\n  useEffect(() => {\n    fetch(`/api/search?q=${query}`).then((r) => r.json()).then(setResults);\n  }, [query]);\n  return results;\n}'),
     ed('/home/alex/web-dashboard/src/hooks/useSearch.ts', '    fetch(`/api/search?q=${query}`).then((r) => r.json()).then(setResults);', '    const ctrl = new AbortController();\n    const timer = setTimeout(() => {\n      fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: ctrl.signal })\n        .then((r) => r.json()).then(setResults).catch(() => {});\n    }, 250);\n    return () => { clearTimeout(timer); ctrl.abort(); };'))),
 S('ml', 'Debug NaN loss during training',
   Q('Loss becomes NaN around step 3,000 in the transformer run. Seed 1 only. Help me track it down.',
     'The NaN comes from the attention softmax in float16: with a few very large logits, `exp` overflows. Computing the scores in float32 before the softmax removes it. I also added gradient clipping at 1.0 as a safety net.',
     th('Only one seed, only after a few thousand steps: likely numerical, not a data bug. Check mixed precision and the attention implementation.'),
     sh('grep -n "nan\\|inf" logs/run_seed1.log | head', '3012: step 3011 loss 2.31\n3013: step 3012 loss nan'),
     rd('/home/alex/ml-experiments/models/attention.py', 'def forward(self, x):\n    q, k, v = self.qkv(x).chunk(3, dim=-1)\n    scores = (q @ k.transpose(-2, -1)) * self.scale\n    attn = scores.softmax(dim=-1)\n    return attn @ v'),
     ed('/home/alex/ml-experiments/models/attention.py', '    attn = scores.softmax(dim=-1)', '    attn = scores.float().softmax(dim=-1).to(v.dtype)'),
     sh('python train.py --seed 1 --steps 6000 2>&1 | tail -2', 'step 5999 loss 1.87\nfinished: no NaN in 6000 steps')),
   Q('Add a guard that stops the run and saves a checkpoint if loss is not finite.', 'Added `check_finite(loss)`; on a non-finite loss it saves `crash.pt` with the optimizer state and the last batch indices, then raises.',
     ed('/home/alex/ml-experiments/train.py', 'loss = step(model, batch)', 'loss = step(model, batch)\n        if not torch.isfinite(loss):\n            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": step_i}, "crash.pt")\n            raise FloatingPointError(f"non-finite loss at step {step_i}")'),
     sh('python -m pytest tests/test_guard.py -q', '.                                                                        [100%]\n1 passed in 0.9s'),),
   Q('Summarize what we found in two sentences for the lab notes.', 'Seed 1 diverged at step ~3,000 because float16 attention scores overflowed in the softmax; computing the softmax in float32 and clipping gradients at 1.0 fixes it with no measurable accuracy change.'),
   compact=(2, 'The user is debugging NaN losses in a transformer run (seed 1, ~step 3,000). Root cause: float16 overflow in attention softmax in models/attention.py. Fixed by casting scores to float32 before softmax and adding grad clipping at 1.0. A finite-loss guard was added to train.py.')),
 S('ml', 'Plot confusion matrix with seaborn',
   Q('Make a confusion matrix plot for the validation predictions in `preds.npz`. Row-normalized, readable class labels.', 'The script `plot_confusion.py` reads `preds.npz`, row-normalizes the matrix, and writes `figures/confusion.png` at 200 dpi. Class names come from `classes.json` and are rotated so the long ones fit.',
     sh('python -c "import numpy as np; d=np.load(\'preds.npz\'); print({k: d[k].shape for k in d})"', "{'y_true': (10000,), 'y_pred': (10000,)}"),
     wr('/home/alex/ml-experiments/plot_confusion.py', 'import json, numpy as np, seaborn as sns, matplotlib.pyplot as plt\nfrom sklearn.metrics import confusion_matrix\n\nd = np.load("preds.npz"); classes = json.load(open("classes.json"))\ncm = confusion_matrix(d["y_true"], d["y_pred"], normalize="true")\nfig, ax = plt.subplots(figsize=(7, 6))\nsns.heatmap(cm, annot=True, fmt=".2f", cmap="Blues", xticklabels=classes, yticklabels=classes, ax=ax)\nax.set_xlabel("Predicted"); ax.set_ylabel("True")\nplt.xticks(rotation=45, ha="right"); plt.tight_layout()\nplt.savefig("figures/confusion.png", dpi=200)'),
     sh('python plot_confusion.py && ls -la figures/confusion.png', '-rw-r--r-- 1 alex alex 96431 Jun  3 11:20 figures/confusion.png'))),
 S('infra', 'Add GitHub Actions cache for Docker builds',
   Q('Docker builds take 9 minutes in CI. Add layer caching to the workflow.', 'Added `docker/build-push-action` with the GitHub Actions cache backend (`type=gha, mode=max`). The first run is unchanged, but a rebuild without dependency changes now takes about 1m40s instead of 9 minutes (measured on two consecutive runs).',
     rd('/home/alex/infra/.github/workflows/build.yml', 'jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: docker build -t api:${{ github.sha }} docker/api'),
     ed('/home/alex/infra/.github/workflows/build.yml', '      - run: docker build -t api:${{ github.sha }} docker/api', '      - uses: docker/setup-buildx-action@v3\n      - uses: docker/build-push-action@v6\n        with:\n          context: docker/api\n          tags: api:${{ github.sha }}\n          cache-from: type=gha\n          cache-to: type=gha,mode=max'))),
 S('web', 'Upgrade React Router to v7',
   Q('Upgrade react-router-dom from v6 to v7. List what breaks before changing anything.', 'v7 merges the DOM package into `react-router`, so the main change is imports. Nothing else in the app uses removed APIs. I listed the 14 files with imports and then updated them with a codemod-style `sed`; type-check and tests pass.',
     th('v7 consolidates packages. First, grep for imports and for the future flags that were opt-in in v6.'),
     gr('react-router-dom', 'src/main.tsx:3:import { createBrowserRouter } from "react-router-dom";\nsrc/routes.tsx:1:import { Outlet, Link } from "react-router-dom";\n... (14 matches in 14 files)'),
     sh('npm uninstall react-router-dom && npm install react-router@7', 'removed 2 packages, and added 3 packages in 6s'),
     sh("grep -rl 'react-router-dom' src | xargs sed -i 's#react-router-dom#react-router#g'", ''),
     sh('npx tsc --noEmit && npx vitest run', ' Test Files  23 passed (23)\n      Tests  141 passed (141)'))),
 S('rust', 'Handle SIGINT gracefully in the CLI',
   Q('When I press Ctrl-C during `stash sync`, it leaves a half-written temp file. Handle SIGINT so it cleans up.', 'Added a `ctrlc` handler that sets an `AtomicBool`; the copy loop checks it between chunks, removes the temp file and exits with status 130. I tested it by sending SIGINT during a large copy.',
     rd('/home/alex/rust-cli/src/sync.rs', 'pub fn sync(src: &Path, dst: &Path) -> io::Result<()> {\n    let tmp = dst.with_extension("part");\n    let mut out = File::create(&tmp)?;\n    io::copy(&mut File::open(src)?, &mut out)?;\n    fs::rename(tmp, dst)\n}'),
     ed('/home/alex/rust-cli/src/sync.rs', '    io::copy(&mut File::open(src)?, &mut out)?;', '    let mut input = File::open(src)?;\n    let mut buf = [0u8; 64 * 1024];\n    loop {\n        if INTERRUPTED.load(Ordering::SeqCst) {\n            drop(out);\n            let _ = fs::remove_file(&tmp);\n            std::process::exit(130);\n        }\n        let n = input.read(&mut buf)?;\n        if n == 0 { break; }\n        out.write_all(&buf[..n])?;\n    }'),
     sh('timeout -s INT 1 cargo run -q -- sync big.bin /tmp/out.bin; echo "exit=$?"; ls /tmp/out.*', 'exit=130\nls: cannot access \'/tmp/out.*\': No such file or directory'))),
 S('blog', 'Optimize images with sharp at build time',
   Q('Add an image step to the build: resize anything over 1600px wide and emit WebP next to the original.', 'The build now walks `content/images`, resizes images wider than 1600 px, and writes a `.webp` next to each original. Output is cached by file hash, so unchanged images are skipped and a full rebuild went from 22 s to 1.3 s. Total image weight dropped by 63%.',
     sh('npm install sharp', 'added 18 packages in 4s'),
     wr('/home/alex/blog/scripts/images.mjs', 'import sharp from "sharp";\nimport { readdir } from "node:fs/promises";\n\nfor (const f of await readdir("content/images")) {\n  if (!/\\.(png|jpe?g)$/i.test(f)) continue;\n  await sharp(`content/images/${f}`)\n    .resize({ width: 1600, withoutEnlargement: true })\n    .webp({ quality: 80 })\n    .toFile(`public/images/${f.replace(/\\.\\w+$/, ".webp")}`);\n}'),
     sh('node scripts/images.mjs && du -sh content/images public/images', '14M\tcontent/images\n5.2M\tpublic/images'))),
 S('infra', 'Debug failing Terraform plan in staging',
   Q('`terraform plan` in staging fails with "Error acquiring the state lock". Nobody else is running anything.', 'A previous CI run was cancelled mid-apply, leaving a stale lock entry in the DynamoDB table. I confirmed the lock owner was that run (ID `7c3e91d0`), checked nothing was still running, and released it with `terraform force-unlock`. The plan now runs cleanly and shows no changes.',
     th('A stale lock after a cancelled job is the usual cause. Verify nobody is really holding it before force-unlocking.'),
     sh('terraform -chdir=environments/staging plan', 'Error: Error acquiring the state lock\n\nLock Info:\n  ID:        7c3e91d0-52b4-9a1e-0d3f-8ab6c44e1f20\n  Operation: OperationTypeApply\n  Who:       runner@ci-staging\n  Created:   2026-06-16 09:12:44 UTC', err=True),
     sh('gh run list --workflow=apply.yml --limit 3', 'completed  cancelled  Apply staging  main  2026-06-16T09:12:40Z\ncompleted  success    Apply staging  main  2026-06-15T16:03:11Z'),
     sh('terraform -chdir=environments/staging force-unlock -force 7c3e91d0-52b4-9a1e-0d3f-8ab6c44e1f20', 'Terraform state has been successfully unlocked!'),
     sh('terraform -chdir=environments/staging plan', 'No changes. Your infrastructure matches the configuration.'))),
 S('dot', 'Port Neovim config to Lua',
   Q('Port my `init.vim` to Lua with lazy.nvim. Keep the same keymaps and the Treesitter setup.', 'Ported. The config is split into `lua/options.lua`, `lua/keymaps.lua` and `lua/plugins.lua`, and plugins are lazy-loaded by event. Startup time dropped from 148 ms to 51 ms (`nvim --startuptime`). All the old leader mappings are kept.',
     rd('/home/alex/dotfiles/nvim/init.vim', 'set number relativenumber\nset expandtab shiftwidth=2\nlet mapleader = " "\nnnoremap <leader>ff :Telescope find_files<CR>\nnnoremap <leader>fg :Telescope live_grep<CR>'),
     wr('/home/alex/dotfiles/nvim/lua/keymaps.lua', 'vim.g.mapleader = " "\nlocal map = vim.keymap.set\nmap("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc = "Find files" })\nmap("n", "<leader>fg", "<cmd>Telescope live_grep<cr>", { desc = "Live grep" })'),
     sh('nvim --headless --startuptime /tmp/st.log +q && tail -1 /tmp/st.log', '051.204  000.402: --- NVIM STARTED ---'))),
 S('ml', 'Speed up data loader with multiprocessing',
   Q('GPU utilization sits around 40% and `nvidia-smi` shows it idling. I suspect the data loader.', 'It is the loader: JPEG decoding ran in the main process (`num_workers=0`). With 8 workers, pinned memory and `persistent_workers=True`, GPU utilization went from 41% to 93% and an epoch from 214 s to 96 s.',
     gr('DataLoader', 'train.py:57:loader = DataLoader(ds, batch_size=128, shuffle=True)'),
     ed('/home/alex/ml-experiments/train.py', 'loader = DataLoader(ds, batch_size=128, shuffle=True)', 'loader = DataLoader(ds, batch_size=128, shuffle=True, num_workers=8,\n                    pin_memory=True, persistent_workers=True, prefetch_factor=4)'),
     sh('python train.py --epochs 1 --profile', 'epoch 1  time 96.3s  gpu_util 93%  samples/s 1038'))),
 S('web', 'Write unit tests for the date formatter',
   Q('`formatRelativeDate` has no tests and keeps breaking around midnight. Write tests, including time zone edge cases.', 'Wrote 11 tests covering "just now", minutes, hours, yesterday, and dates across a DST change. Two of them failed at first and exposed a real bug: the function compared calendar days in UTC rather than the viewer\'s zone. Fixed with `Intl.DateTimeFormat` day keys; all 11 pass.',
     rd('/home/alex/web-dashboard/src/lib/formatRelativeDate.ts', 'export function formatRelativeDate(d: Date, now = new Date()) {\n  const diff = (now.getTime() - d.getTime()) / 1000;\n  if (diff < 60) return "just now";\n  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;\n  if (d.toISOString().slice(0, 10) === now.toISOString().slice(0, 10)) return "today";\n  return "earlier";\n}'),
     sh('npx vitest run src/lib/formatRelativeDate.test.ts', ' ❯ src/lib/formatRelativeDate.test.ts (11)\n   × yesterday at 23:30 local (TZ=America/Los_Angeles)\n   × today after local midnight\n\n Tests  2 failed | 9 passed (11)', err=True),
     ed('/home/alex/web-dashboard/src/lib/formatRelativeDate.ts', '  if (d.toISOString().slice(0, 10) === now.toISOString().slice(0, 10)) return "today";', '  const day = (x: Date) => new Intl.DateTimeFormat("en-CA").format(x);\n  if (day(d) === day(now)) return "today";'),
     sh('npx vitest run src/lib/formatRelativeDate.test.ts', ' ✓ src/lib/formatRelativeDate.test.ts (11)\n\n Tests  11 passed (11)'))),
 S('blog', 'Fix broken code highlighting in dark theme',
   Q('In dark mode, code blocks on the blog are unreadable: dark grey text on a dark background.', 'The highlighter theme only had light-mode token colors. I added a dark palette scoped under `[data-theme="dark"]` and moved the token colors into CSS variables so both themes share one stylesheet. Contrast now passes WCAG AA for all token types.',
     rd('/home/alex/blog/assets/code.css', '.token.comment { color: #6a737d; }\n.token.keyword { color: #d73a49; }\n.token.string  { color: #032f62; }'),
     ed('/home/alex/blog/assets/code.css', '.token.string  { color: #032f62; }', '.token.string  { color: var(--tok-string); }\n:root { --tok-string: #032f62; }\n[data-theme="dark"] { --tok-string: #9ecbff; --tok-comment: #8b949e; --tok-keyword: #ff7b72; }'))),
 S('rust', 'Publish v0.3.0 to crates.io',
   Q('Prepare the 0.3.0 release: bump the version, update the changelog, and do a dry-run publish.', 'Bumped to 0.3.0, added a changelog entry with the three user-facing changes, and `cargo publish --dry-run` succeeds. I did not run the real publish, since it cannot be undone; the command is `cargo publish`.',
     rd('/home/alex/rust-cli/CHANGELOG.md', '# Changelog\n\n## 0.2.1\n- Fix crash on empty config\n'),
     ed('/home/alex/rust-cli/CHANGELOG.md', '# Changelog\n', '# Changelog\n\n## 0.3.0\n- Config moved to TOML (the old `~/.stashrc` still works, with a warning)\n- New `--json` flag for `list`\n- Ctrl-C during `sync` now cleans up temp files\n'),
     sh('cargo publish --dry-run', '   Packaging stash v0.3.0 (/home/alex/rust-cli)\n   Verifying stash v0.3.0\n   Compiling stash v0.3.0\n    Finished dev [unoptimized + debuginfo] target(s) in 6.12s\n   Uploading stash v0.3.0\nwarning: aborting upload due to dry run'))),
 S('web', 'Implement CSV export for reports',
   Q('Add an "Export CSV" button to the reports page. It should stream, because some reports have 500k rows. Look at how reports are queried first (use a subagent).', 'The new `GET /api/reports/:id/export.csv` streams rows from a database cursor through a CSV transform, so memory stays flat. A 500k-row report downloads in about 6 seconds and the server process peaks at 90 MB. The button just links to the endpoint.',
     ag('Inspect report queries', 'Read server/reports/*.ts and tell me how a report query is built, and whether it can be turned into a cursor or stream.',
        'Reports are built in `server/reports/query.ts` as a single Drizzle query that returns all rows. It can be run with `.iterator()` for a cursor. Column labels live in `server/reports/columns.ts`.',
        [gr('export', 'server/reports/index.ts:12:// TODO: export'), rd('/home/alex/web-dashboard/server/reports/query.ts', 'export async function runReport(def: ReportDef) {\n  return db.select(def.columns).from(def.table).where(def.where);\n}')]),
     wr('/home/alex/web-dashboard/server/reports/export.ts', 'import { stringify } from "csv-stringify";\nimport { pipeline } from "node:stream/promises";\n\nexport async function exportCsv(def: ReportDef, res: Response) {\n  res.setHeader("Content-Type", "text/csv");\n  res.setHeader("Content-Disposition", `attachment; filename="${def.slug}.csv"`);\n  const rows = runReport(def).iterator();\n  await pipeline(rows, stringify({ header: true, columns: columnLabels(def) }), res);\n}'),
     sh('curl -s -o /dev/null -w "%{size_download} bytes in %{time_total}s\\n" localhost:3000/api/reports/42/export.csv', '48211930 bytes in 6.1s')),
   Q('Add a test that checks the header row and one data row.', 'Added `export.test.ts`; it feeds a three-row fixture through `exportCsv` into a buffer and asserts the header and the first row. Passing.')),
 S('ml', 'Evaluate ViT vs ResNet on small dataset',
   Q('Compare ViT-S/16 and ResNet-50 when fine-tuned on only 2,000 labeled images. Use the same augmentation and 3 seeds each.', 'Results over 3 seeds (mean ± std top-1): ResNet-50 84.2 ± 0.6, ViT-S/16 81.9 ± 1.1. With this little data the convolutional prior wins, and ViT is also noisier across seeds. Both used the same schedule, with 5 epochs of warmup for ViT.',
     sh('python run_sweep.py --models resnet50 vit_s16 --seeds 0 1 2 --n-train 2000', 'resnet50  seed0 84.6  seed1 83.9  seed2 84.1\nvit_s16   seed0 80.7  seed1 82.8  seed2 82.2'),
     wr('/home/alex/ml-experiments/reports/vit_vs_resnet.md', '# ViT-S/16 vs ResNet-50, 2k labeled images\n\n| model | top-1 (mean ± std) |\n|---|---|\n| ResNet-50 | 84.2 ± 0.6 |\n| ViT-S/16 | 81.9 ± 1.1 |'))),
 S('infra', 'Set up Prometheus alert for disk usage',
   Q('Add a Prometheus alert that fires when any node has less than 15% disk free for 10 minutes, and route it to the #ops Slack channel.', 'Added the `NodeDiskLow` rule (warning at under 15% free for 10 minutes, critical at under 5%) and an Alertmanager route that sends severity=critical to PagerDuty and everything else to #ops. `promtool check rules` passes.',
     wr('/home/alex/infra/monitoring/rules/disk.yml', 'groups:\n  - name: disk\n    rules:\n      - alert: NodeDiskLow\n        expr: node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes < 0.15\n        for: 10m\n        labels: { severity: warning }\n        annotations:\n          summary: "{{ $labels.instance }} has {{ $value | humanizePercentage }} disk free on {{ $labels.mountpoint }}"'),
     sh('promtool check rules monitoring/rules/disk.yml', 'Checking monitoring/rules/disk.yml\n  SUCCESS: 1 rules found'))),
 S('dot', 'Write install script with idempotent symlinks',
   Q('Write an `install.sh` that symlinks everything in this repo into $HOME, backing up existing files once, and is safe to re-run.', 'The script links each package directory with `ln -sfn`, moves any existing real file to `*.bak` only the first time, and prints one line per action. Running it twice shows "ok (already linked)" for everything and changes nothing.',
     wr('/home/alex/dotfiles/install.sh', '#!/usr/bin/env bash\nset -euo pipefail\nlink() {\n  local src=$1 dst=$2\n  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then echo "ok (already linked) $dst"; return; fi\n  if [ -e "$dst" ] && [ ! -L "$dst" ]; then mv "$dst" "$dst.bak"; echo "backed up $dst"; fi\n  mkdir -p "$(dirname "$dst")"; ln -sfn "$src" "$dst"; echo "linked $dst"\n}\nlink "$PWD/zsh/.zshrc" "$HOME/.zshrc"\nlink "$PWD/tmux/.tmux.conf" "$HOME/.tmux.conf"\nlink "$PWD/nvim" "$HOME/.config/nvim"'),
     sh('HOME=$(mktemp -d) bash install.sh && echo --- && HOME=$HOME bash install.sh', 'linked /tmp/tmp.k3J/.zshrc\nlinked /tmp/tmp.k3J/.tmux.conf\nlinked /tmp/tmp.k3J/.config/nvim\n---\nok (already linked) /tmp/tmp.k3J/.zshrc\nok (already linked) /tmp/tmp.k3J/.tmux.conf\nok (already linked) /tmp/tmp.k3J/.config/nvim'))),
 S('web', 'Reduce bundle size with code splitting',
   Q('The main bundle is 1.4 MB. Find out what is big and split it up.', 'The biggest items were `moment` with all locales (290 KB), a charting library loaded on every page (410 KB), and a markdown editor only used in settings (180 KB). I lazy-loaded the chart and editor routes and imported only the English locale. The initial JS went from 1.4 MB to 520 KB.',
     sh('npx vite-bundle-visualizer --output stats.json && node scripts/top-chunks.js stats.json', '410 KB  chart.js\n290 KB  moment (locales)\n180 KB  @uiw/react-md-editor\n 96 KB  lodash'),
     ed('/home/alex/web-dashboard/src/routes.tsx', 'import Reports from "./pages/Reports";', 'const Reports = lazy(() => import("./pages/Reports"));'),
     sh('npm run build | tail -4', 'dist/assets/index-9f3b1c.js      518.40 kB │ gzip: 162.77 kB\ndist/assets/Reports-c71a02.js    412.10 kB │ gzip: 131.02 kB'))),
 S('rust', 'Add shell completions generation',
   Q('Add `stash completions <shell>` that prints a completion script using clap_complete.', 'Added the `completions` subcommand for bash, zsh, fish and PowerShell. I verified the zsh output sources cleanly, and documented the one-liner in the README.',
     sh('cargo add clap_complete', '      Adding clap_complete v4.5.2 to dependencies'),
     ed('/home/alex/rust-cli/src/main.rs', 'Command::List => {', 'Command::Completions { shell } => {\n            clap_complete::generate(shell, &mut Cli::command(), "stash", &mut std::io::stdout());\n        }\n        Command::List => {'),
     sh('cargo run -q -- completions zsh | head -3', '#compdef stash\n\nautoload -U is-at-least'))),
 S('web', 'Accessibility audit of the login form',
   Q('Run an accessibility pass on the login form and fix what you find.', 'Found and fixed five issues: missing `<label>` associations, an error message not announced to screen readers (now `role="alert"`), placeholder text used as the only label, a focus ring removed by CSS, and a 3.1:1 contrast on the helper text (now 4.8:1). axe reports no violations.',
     rd('/home/alex/web-dashboard/src/pages/Login.tsx', '<form onSubmit={onSubmit}>\n  <input type="email" placeholder="Email" value={email} onChange={...} />\n  <input type="password" placeholder="Password" />\n  {error && <div className="error">{error}</div>}\n  <button>Sign in</button>\n</form>'),
     ed('/home/alex/web-dashboard/src/pages/Login.tsx', '  <input type="email" placeholder="Email" value={email} onChange={...} />', '  <label htmlFor="email">Email</label>\n  <input id="email" type="email" autoComplete="username" value={email} onChange={...} />'),
     sh('npx playwright test a11y/login.spec.ts', '  1 passed (3.4s)  (axe: 0 violations)'))),
 S('blog', 'Write post about SQLite WAL mode',
   Q('Write a 600-word post explaining SQLite WAL mode for web developers. Practical, with a benchmark section I can fill in later.', 'Draft saved. It explains the rollback journal versus the write-ahead log with a small diagram in ASCII, shows `PRAGMA journal_mode=WAL;`, covers readers not blocking the writer, and ends with the checkpointing caveat. The benchmark section is a clearly marked TODO.',
     wr('/home/alex/blog/content/drafts/sqlite-wal.md', '---\ntitle: "SQLite WAL mode in plain words"\ndraft: true\n---\n\nBy default SQLite uses a rollback journal: before changing a page it copies the old one aside. Readers and the writer take turns.\n\nWAL flips this around. Changes are appended to a separate log, and readers keep reading the main file plus whatever the log says is committed.\n\n```sql\nPRAGMA journal_mode=WAL;\n```\n\n## Benchmarks\n\nTODO: run 8 readers + 1 writer on the same file.'))),
 S('ml', 'Set up experiment tracking with MLflow',
   Q('Add MLflow tracking to the training script: params, per-epoch metrics, and the final model artifact.', 'Training now logs every CLI argument as params, loss/accuracy per epoch, and the best checkpoint as an artifact. The tracking URI comes from `MLFLOW_TRACKING_URI`, with a local `./mlruns` fallback. I ran a 2-epoch smoke test and the run shows up in `mlflow ui`.',
     sh('pip install mlflow && python -c "import mlflow; print(mlflow.__version__)"', '2.14.1'),
     ed('/home/alex/ml-experiments/train.py', 'for epoch in range(args.epochs):', 'mlflow.log_params(vars(args))\nfor epoch in range(args.epochs):'),
     ed('/home/alex/ml-experiments/train.py', '    print(f"epoch {epoch}', '    mlflow.log_metrics({"val_acc": val_acc, "train_loss": train_loss}, step=epoch)\n    print(f"epoch {epoch}'),
     sh('python train.py --epochs 2 && ls mlruns/0', 'epoch 1  val_acc 0.412\nepoch 2  val_acc 0.538\n3a1b9c0d2e4f4f5a8b6c7d8e9f001122'))),
 S('infra', 'Migrate cron jobs to systemd timers',
   Q('Three cron jobs on the backup host fail silently. Convert them to systemd timers with logging and retries.', 'Created `backup.service` with its `backup.timer` (daily at 02:30, `Persistent=true` so missed runs happen after boot), plus matching units for log rotation and cleanup. Failures now show up in `journalctl -u backup` and `OnFailure=` sends a notification. Cron entries were removed.',
     sh('crontab -l', '30 2 * * * /opt/backup/run.sh >/dev/null 2>&1\n0 4 * * 0 /opt/backup/rotate.sh >/dev/null 2>&1\n15 * * * * /opt/backup/cleanup.sh >/dev/null 2>&1'),
     wr('/home/alex/infra/hosts/backup/backup.timer', '[Unit]\nDescription=Nightly backup\n\n[Timer]\nOnCalendar=*-*-* 02:30:00\nPersistent=true\nRandomizedDelaySec=5min\n\n[Install]\nWantedBy=timers.target'),
     sh('systemd-analyze verify hosts/backup/backup.service hosts/backup/backup.timer && echo ok', 'ok'))),
 S('web', 'Add rate limiting to the API',
   Q('Add rate limiting: 100 requests/minute per IP, and 5/minute on the login endpoint. Return proper headers.', 'Implemented a sliding-window limiter backed by Redis (an in-memory fallback in development). Responses carry `RateLimit-Limit`, `RateLimit-Remaining` and `Retry-After` on 429. The login route has its own stricter limiter. A load test confirmed request 101 gets a 429.',
     rd('/home/alex/web-dashboard/server/app.ts', 'const app = express();\napp.use(cors());\napp.use(express.json());\napp.use("/api", routes);'),
     wr('/home/alex/web-dashboard/server/middleware/rateLimit.ts', 'import rateLimit from "express-rate-limit";\nimport { RedisStore } from "rate-limit-redis";\n\nexport const apiLimiter = rateLimit({\n  windowMs: 60_000, limit: 100, standardHeaders: "draft-7", legacyHeaders: false,\n  store: process.env.REDIS_URL ? new RedisStore({ sendCommand: (...a) => redis.sendCommand(a) }) : undefined,\n});\nexport const loginLimiter = rateLimit({ windowMs: 60_000, limit: 5, standardHeaders: "draft-7" });'),
     ed('/home/alex/web-dashboard/server/app.ts', 'app.use("/api", routes);', 'app.use("/api", apiLimiter);\napp.post("/api/login", loginLimiter);\napp.use("/api", routes);'),
     sh('for i in $(seq 103); do curl -s -o /dev/null -w "%{http_code}\\n" localhost:3000/api/health; done | sort | uniq -c', '    100 200\n      3 429'))),
 S('rust', 'Fix Windows path handling in tests',
   Q('CI is red on the Windows runner: three tests compare paths with forward slashes. Fix them.', 'The tests built expected strings with `/` while the code returns `PathBuf`s with backslashes on Windows. I changed the assertions to compare `Path` values (which normalizes separators) and used `Path::join` to build expectations. The Windows job is green on the branch.',
     sh('gh run view --log-failed | head -12', 'test config::tests::expands_home ... FAILED\n  left: "C:\\\\Users\\\\runner\\\\notes"\n right: "C:/Users/runner/notes"', err=True),
     ed('/home/alex/rust-cli/src/config.rs', 'assert_eq!(expand("~/notes").to_str().unwrap(), format!("{}/notes", home));', 'assert_eq!(expand("~/notes"), Path::new(&home).join("notes"));'),
     sh('cargo test', 'test result: ok. 14 passed; 0 failed'))),
 S('ml', 'Refactor training script into modules',
   Q('`train.py` is 600 lines. Split it into data, model, and training modules without changing behavior.', 'Split into `data.py` (datasets and loaders), `models/` (architectures and the registry), `engine.py` (train and eval loops) and a thin `train.py` that only parses arguments. To verify behavior, I ran seed 0 for 200 steps before and after: the loss curves match to the 6th decimal.',
     sh('wc -l train.py && grep -n "^def \\|^class " train.py | head -20', '612 train.py\n24:def get_transforms(train):\n41:class SubsetDataset(Dataset):\n78:def build_model(name):\n133:def evaluate(model, loader):\n171:def main():'),
     sh('python train.py --seed 0 --steps 200 | md5sum', 'b1e7c0a9d83f4b2a6c5e1f7d9a0b3c42  -'),
     wr('/home/alex/ml-experiments/engine.py', 'import torch\n\ndef evaluate(model, loader, device):\n    model.eval(); correct = total = 0\n    with torch.no_grad():\n        for x, y in loader:\n            pred = model(x.to(device)).argmax(-1).cpu()\n            correct += (pred == y).sum().item(); total += len(y)\n    return correct / total'),
     sh('python train.py --seed 0 --steps 200 | md5sum', 'b1e7c0a9d83f4b2a6c5e1f7d9a0b3c42  -')),
   Q('Add type hints and a short docstring to the public functions in engine.py.', 'Done for `evaluate` and `train_epoch`. `mypy engine.py` reports no errors.'),
   Q('Now write the README section describing the new layout.', 'Added a "Project layout" section with a tree and one line per module, plus the command to run a smoke test.'),
   compact=(1, 'Refactoring ml-experiments/train.py (612 lines) into data.py, models/, engine.py, and a thin train.py. Behavior preserved: md5 of the first 200 steps of loss output for seed 0 is identical before and after. engine.py has evaluate(); train_epoch still to be moved.')),
 S('dot', 'Add git aliases and a better prompt',
   Q('Add a few useful git aliases and show the branch and dirty state in my zsh prompt.', 'Added aliases `st`, `lg` (compact graph log), `co`, `amend` and `undo` (soft-reset the last commit) to `gitconfig`, and a prompt segment that shows the branch, a `*` when dirty, and ahead/behind arrows. It uses `git status --porcelain=v2 --branch` once per prompt, so it stays fast.',
     rd('/home/alex/dotfiles/git/.gitconfig', '[user]\n  name = Alex Doe\n[core]\n  editor = nvim\n  pager = delta'),
     ed('/home/alex/dotfiles/git/.gitconfig', '[core]', '[alias]\n  st = status -sb\n  lg = log --graph --oneline --decorate -20\n  co = checkout\n  amend = commit --amend --no-edit\n  undo = reset --soft HEAD~1\n[core]'),
     sh('git lg | head -3', '* 4f2a91c (HEAD -> main) Add install script\n* a03be77 Port Neovim config to Lua\n* 91d0c5e Fix tmux colors over SSH'))),
 S('web', 'Replace moment.js with date-fns',
   Q('Replace moment.js with date-fns across the app. List the call sites first.', 'There were 31 call sites in 12 files, mostly `format`, `fromNow` and `add`. Replaced them with `date-fns` equivalents (`format`, `formatDistanceToNow`, `addDays`) and removed `moment` from `package.json`. The bundle shrank by another 72 KB gzip; all 141 tests pass.',
     gr('moment', 'src/lib/dates.ts:1:import moment from "moment";\nsrc/lib/dates.ts:6:  return moment(d).format("MMM D, YYYY");\nsrc/pages/Reports.tsx:41:  moment().subtract(30, "days")\n... (31 matches in 12 files)'),
     ed('/home/alex/web-dashboard/src/lib/dates.ts', '  return moment(d).format("MMM D, YYYY");', '  return format(d, "MMM d, yyyy");'),
     sh('npm uninstall moment && npx tsc --noEmit && npx vitest run', 'removed 2 packages\n Test Files  23 passed (23)\n      Tests  141 passed (141)'))),
 S('infra', 'Harden nginx config and add security headers',
   Q('Harden the nginx config on the public proxy: TLS settings, security headers, and hide the version.', 'Applied: TLS 1.2+ only with modern ciphers, HSTS (1 year), `X-Content-Type-Options`, `X-Frame-Options: DENY`, a conservative `Content-Security-Policy`, and `server_tokens off`. `nginx -t` passes, and the securityheaders scan went from F to A. I left CSP in report-only mode first so nothing breaks silently.',
     rd('/home/alex/infra/hosts/proxy/nginx.conf', 'server {\n  listen 443 ssl;\n  server_name app.example.com;\n  ssl_certificate /etc/ssl/app.crt;\n  ssl_certificate_key /etc/ssl/app.key;\n  location / { proxy_pass http://127.0.0.1:3000; }\n}'),
     ed('/home/alex/infra/hosts/proxy/nginx.conf', '  location / { proxy_pass http://127.0.0.1:3000; }', '  server_tokens off;\n  ssl_protocols TLSv1.2 TLSv1.3;\n  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n  add_header X-Content-Type-Options nosniff always;\n  add_header X-Frame-Options DENY always;\n  add_header Content-Security-Policy-Report-Only "default-src \'self\'" always;\n  location / { proxy_pass http://127.0.0.1:3000; }'),
     sh('nginx -t', 'nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\nnginx: configuration file /etc/nginx/nginx.conf test is successful'))),
]

# 日期（连续几天、一天两个会话，形成起伏）
D = [(3,10),(3,11),(3,12),(3,12),  (4,2),(4,14),(4,21),(4,22),(4,22),(4,23),
     (5,4),(5,5),(5,5),(5,5),(5,6),(5,19),(5,20),(5,21),  (6,2),(6,16),(6,16),(6,17),(6,29),
     (7,8),(7,9),(7,27),  (8,4),(8,11),(8,12),(8,12),(8,12),(8,13),
     (9,1),(9,2),(9,2),(9,3),(9,8),(9,16),(9,17),(9,17),(9,17),(9,22),(9,23)]
assert len(D) == len(SESSIONS), (len(D), len(SESSIONS))
ISO = lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def stamp(rows, start):
    t = start; first = True
    for r in rows:
        if 'timestamp' not in r: continue
        if first: first = False
        elif r.get('origin') == {'kind': 'human'}: t += timedelta(seconds=RND.randint(40, 420))
        elif r['type'] == 'user' and isinstance(r['message']['content'], list): t += timedelta(seconds=RND.randint(1, 9))
        else: t += timedelta(seconds=RND.randint(3, 28))
        r['timestamp'] = ISO(t)

def build_cc(home):
    pdir = os.path.join(home, '.claude', 'projects'); n_main = n_sub = 0; desk = {}
    for idx, (sd, (mo, day)) in enumerate(zip(SESSIONS, D)):
        cwd = PROJECTS[sd['proj']]; mf.CWD = cwd
        sid = U('demo-session-%d' % idx); s = mf.Sess(sid); k = 's%d' % idx; c = [0]
        def nm(p='x'): c[0] += 1; return f'{k}-{p}{c[0]}'
        def mid(): c[0] += 1; return f'msg_{k}_{c[0]}'
        agents = []
        for ti, (prompt, ans, steps) in enumerate(sd['turns']):
            if sd['compact'] and sd['compact'][0] == ti:
                b = s.base('system', U(nm('bound')), 'x'); b.update(subtype='compact_boundary', content='Conversation compacted', level='info', isMeta=False,
                    compactMetadata={'trigger': 'auto', 'preTokens': 148000}, logicalParentUuid=s.rows[-2]['uuid'])
                cs = s.base('user', U(nm('sum')), 'x'); cs.update(isCompactSummary=True, isVisibleInTranscriptOnly=True,
                    message={'role': 'user', 'content': 'This session is being continued from a previous conversation that ran out of context. Summary:\n' + sd['compact'][1]})
            s.user(prompt, nm('u'))
            pend = []
            def flush(m):
                for p in pend: s.asst(nm('a'), m, [think(p[1]) if p[0] == 'th' else txt(p[1])])
                pend.clear()
            for st in steps:
                if st[0] in ('th', 'tx'): pend.append(st); continue
                m = mid(); flush(m)
                if st[0] == 'tool':
                    tid = 'toolu_' + nm('t'); s.asst(nm('a'), m, [tool(tid, st[1], st[2])])
                    s.result(nm('r'), tid, st[3], err=st[4])
                else:   # 子 agent
                    _, desc, ptxt, res, sub = st; tid = 'toolu_' + nm('t'); aid = '%016x' % RND.getrandbits(64)
                    a = s.asst(nm('a'), m, [tool(tid, 'Agent', {'description': desc, 'prompt': ptxt, 'subagent_type': 'Explore'})])
                    s.result(nm('r'), tid, res, tur={'status': 'completed', 'agentId': aid, 'content': [txt(res)]})
                    agents.append((aid, desc, ptxt, res, sub, tid, a))
            m = mid(); flush(m)
            if ans: s.asst(nm('a'), m, [txt(ans)])
        s.raw({'type': 'ai-title', 'aiTitle': sd['title'], 'sessionId': sid})
        start = datetime(2026, mo, day, RND.randint(9, 17), RND.randint(0, 59), RND.randint(0, 59), tzinfo=timezone.utc)
        stamp(s.rows, start)
        folder = os.path.join(pdir, cwd.replace('/', '-'))
        s.dump(os.path.join(folder, sid + '.jsonl')); n_main += 1
        for aid, desc, ptxt, res, sub, tid, a in agents:
            ag = mf.Sess(sid, side=True, agent=aid); ag.task(ptxt, nm('at'))
            for st in sub:
                t2 = 'toolu_' + nm('t'); ag.asst(nm('a'), mid(), [tool(t2, st[1], st[2])]); ag.result(nm('r'), t2, st[3])
            ag.asst(nm('a'), mid(), [txt(res)])
            stamp(ag.rows, datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) + timedelta(seconds=4))
            d = os.path.join(folder, sid, 'subagents'); ag.dump(os.path.join(d, f'agent-{aid}.jsonl')); n_sub += 1
            json.dump({'agentType': 'Explore', 'description': desc, 'toolUseId': tid, 'spawnDepth': 1}, open(os.path.join(d, f'agent-{aid}.meta.json'), 'w'))
        if idx in (6, 15, 27, 37):   # 桌面应用元数据：这几个会话加星标
            desk[sid] = {'cliSessionId': sid, 'title': sd['title'], 'titleSource': 'auto', 'isStarred': True, 'isArchived': False}
    dd = os.path.join(home, 'desktop-meta', 'claude-code-sessions', 'acct', 'org'); os.makedirs(dd, exist_ok=True)
    for i, d in enumerate(desk.values(), 1): json.dump(d, open(os.path.join(dd, f'local_{i:04d}.json'), 'w'))
    return n_main, n_sub, len(desk)

# ───────────── claude.ai 导出包 ─────────────
def ai_ts(mo, day, h, m): return f'2026-{mo:02d}-{day:02d}T{h:02d}:{m:02d}:00.000000Z'
def AI(name, summary, date, turns, att=None, rewrite=None, regen=None, artifact=None):
    """turns=[(问, 答)]；rewrite=(k, 旧问, 旧答)：第 k 轮的问题被改写重发；regen=(k, 初版答)：第 k 轮答案被重新生成；artifact=(k, 标题, 内容)"""
    key = 'ai-' + name[:12]; mo, day = date; h = RND.randint(9, 20); minute = [0]; msgs = []
    def when(): minute[0] += RND.randint(1, 4); return ai_ts(mo, day, h + minute[0] // 60, minute[0] % 60)
    parent = mf.ROOT; n = 0
    for k, (q, a) in enumerate(turns):
        if rewrite and rewrite[0] == k:
            o = mf.am(key, f'oq{k}', parent, 'human', when(), [txt(rewrite[1])]); msgs.append(o)
            msgs.append(mf.am(key, f'oa{k}', o['uuid'], 'assistant', when(), [txt(rewrite[2])]))
        h_ = mf.am(key, f'q{k}', parent, 'human', when(), [txt(q)], att=att if k == 0 else None); msgs.append(h_)
        if regen and regen[0] == k: msgs.append(mf.am(key, f'ra{k}', h_['uuid'], 'assistant', when(), [txt(regen[1])]))
        blocks = [txt(a)]
        if artifact and artifact[0] == k:
            blocks = [tool(f'tu{k}', 'artifacts', {'id': 'readme-draft', 'type': 'text/markdown', 'title': artifact[1], 'command': 'create', 'content': artifact[2]}), txt(a)]
        a_ = mf.am(key, f'a{k}', h_['uuid'], 'assistant', when(), blocks, text=a); msgs.append(a_); parent = a_['uuid']
    return {'uuid': U(key), 'name': name, 'summary': summary, 'created_at': msgs[0]['created_at'], 'updated_at': msgs[-1]['created_at'],
            'account': {'uuid': U('acct')}, 'chat_messages': msgs}

def build_ai(home):
    C = []
    C.append(AI('Draft a cover letter for a data role', 'Cover letter for a junior data analyst position.', (3, 4), [
        ('I\'m applying for a data analyst role at a mid-size logistics company. My resume is attached. Can you draft a cover letter that doesn\'t sound like a template?',
         'Here is a first draft built around the one project in your resume that matches their work:\n\n**Dear Hiring Team,**\n\nLast year I rebuilt the weekly delivery-delay report for a regional courier. The old version took four hours of spreadsheet work every Monday; the new SQL and dashboard pipeline takes six minutes and surfaced a depot that was 18% slower than the others. That kind of unglamorous, decision-changing analysis is what I want to do at your company.\n\nA few things I would bring:\n\n- **SQL and Python**, daily, for cleaning messy operational data\n- **Dashboards** that operations managers actually open\n- **Plain-language writing**: I explain results to people who do not care about p-values\n\nI would welcome the chance to talk about your routing data.\n\nSincerely,\nJordan Rivera'),
        ('Make it shorter, under 200 words, and mention that I am relocating in June.',
         'Shorter version (about 150 words):\n\n**Dear Hiring Team,**\n\nI rebuilt a courier\'s weekly delay report, cutting four hours of manual work to six minutes and exposing one depot running 18% slower than the rest. I want to do that kind of analysis for your operations team.\n\nI work in SQL and Python every day, build dashboards managers actually use, and explain results in plain language. I am relocating to your city in June and can start right after.\n\nI would be glad to talk about your routing data.\n\nSincerely,\nJordan Rivera')],
        att=[{'file_name': 'resume.txt', 'file_size': 1420, 'file_type': 'text/plain', 'extracted_content': 'Jordan Rivera\nData Analyst | SQL, Python, Tableau\n\nExperience\nRegional Courier Co. (2023-2025): rebuilt weekly delivery-delay reporting; cut manual reporting from 4 hours to 6 minutes; identified depot 18% slower than average.\n\nEducation\nB.S. Statistics, State University, 2023'}]))
    C.append(AI('Explain Rust lifetimes with examples', 'Introductory explanation of lifetimes and borrowing.', (3, 18), [
        ('Explain Rust lifetimes like I know C but not Rust.',
         'Think of a lifetime as the compiler\'s answer to a question you already ask in C: "how long is this pointer valid?" In Rust the compiler checks that for you.\n\n```rust\nfn longest<\'a>(a: &\'a str, b: &\'a str) -> &\'a str {\n    if a.len() > b.len() { a } else { b }\n}\n```\n\nThe `\'a` says: the returned reference lives no longer than the shorter of the two inputs. Without it the compiler cannot tell whether you might return a dangling pointer.\n\nThree rules of thumb:\n\n1. Most of the time you write no lifetimes; elision fills them in.\n2. A struct holding a reference needs a lifetime parameter.\n3. If the compiler complains, the fix is often to return an owned `String`.'),
        ('Show me the classic error and how to fix it.',
         'The classic one is returning a reference to a local:\n\n```rust\nfn make() -> &str {\n    let s = String::from("hi");\n    &s        // error[E0106]: missing lifetime specifier\n}\n```\n\nEven with a lifetime, `s` is dropped at the end of the function, so the reference would dangle. Fix it by returning ownership:\n\n```rust\nfn make() -> String {\n    String::from("hi")\n}\n```')]))
    C.append(AI('Plan a 5-day trip to Kyoto', 'Itinerary and budget for five days in Kyoto.', (4, 9), [
        ('Plan a 5-day trip to Kyoto in late October. I like temples, food markets and walking, and I dislike crowds.',
         'Here is a plan that puts the busiest sights early in the morning:\n\n**Day 1: Higashiyama.** Kiyomizu-dera at opening time, then walk Sannenzaka and Ninenzaka. Lunch near Gion, evening stroll along Shirakawa.\n\n**Day 2: Arashiyama.** Go before 8 am: bamboo grove, Tenryu-ji garden, then rent a bike along the Hozu river.\n\n**Day 3: Fushimi Inari + Nishiki Market.** Hike past the first crowded gates to the quiet upper trail, then eat your way through Nishiki.\n\n**Day 4: Northern temples.** Kinkaku-ji, Ryoan-ji and the quiet Daitoku-ji sub-temples.\n\n**Day 5: Day trip to Nara or slow morning** at Philosopher\'s Path before the train.'),
        ('Rough budget per day excluding the hotel?',
         'For one person, roughly:\n\n| Item | Per day |\n|---|---|\n| Food (casual, one nicer meal) | 4,500 to 6,500 yen |\n| Temple and garden entries | 1,000 to 2,000 yen |\n| Local transport (bus/subway) | 600 to 1,200 yen |\n| Snacks, coffee | 800 yen |\n\nAbout **7,000 to 10,000 yen** a day, so 35,000 to 50,000 yen for five days. A bus day pass pays off only on days 1 and 4.')]))
    C.append(AI('Study plan for the AWS Cloud Practitioner exam', 'Four-week plan.', (4, 22), [
        ('I have four weeks and about an hour a day. Make me a study plan for the AWS Cloud Practitioner exam.',
         '**Week 1: Core concepts.** Cloud basics, shared responsibility model, regions and availability zones, IAM.\n**Week 2: Services.** EC2, S3, RDS, Lambda, VPC at the "what is it for" level.\n**Week 3: Pricing and support.** Pricing models, Free Tier, Cost Explorer, support plans, Well-Architected pillars.\n**Week 4: Practice.** Two full practice exams, review every wrong answer, then rest the day before.\n\nTip: flashcards for service names pay off more than reading documentation.')]))
    C.append(AI('Rewrite my LinkedIn summary', 'Tighter, more specific profile summary.', (5, 6), [
        ('Rewrite this LinkedIn summary: "I am a passionate team player with experience in many technologies and a strong desire to learn."',
         'That sentence could describe anyone, so the rewrite needs specifics. Template:\n\n"I build data pipelines that finance teams can trust. Over five years I have moved reporting from spreadsheets to tested SQL models, cutting month-end close by two days. I work mostly in Python, dbt and Airflow, and I like explaining the numbers to people who have to act on them."\n\nSend me your real projects and I will swap in your details.')],
        rewrite=(0, 'Make my LinkedIn summary better: I am a passionate team player with experience in many technologies.', 'Here is a polished version: "Passionate professional with broad technical experience."')))
    C.append(AI('Meal prep ideas for a busy week', 'Five-lunch prep with a shopping list.', (5, 12), [
        ('Give me a vegetarian meal prep plan for five lunches that I can cook in about 90 minutes on Sunday.',
         '**Cook once, assemble five ways:**\n\n- Roast a tray of chickpeas, sweet potato and peppers (35 min)\n- Cook a big pot of quinoa or rice (20 min)\n- Make two sauces: lemon-tahini and peanut-lime (10 min)\n- Boil six eggs, chop raw veg\n\nBowls: Mon Mediterranean, Tue peanut-lime, Wed burrito, Thu egg salad wrap, Fri leftovers frittata.\n\n**Shopping list:** chickpeas, sweet potatoes, peppers, quinoa, tahini, lemons, peanut butter, limes, eggs, tortillas, spinach, cucumber.')], regen=(0, 'Here is a plan: roast vegetables, cook grains, and mix and match through the week.')))
    C.append(AI('Summarize the causes of the 2008 financial crisis', 'Short explainer with three causes.', (5, 20), [
        ('Explain the 2008 financial crisis in plain language, in under 250 words.',
         'Three things stacked on top of each other:\n\n1. **Cheap, careless mortgages.** Banks lent to people who could not repay, because they planned to sell the loans on.\n2. **Packaging risk.** Those loans were bundled into securities and rated safe, so investors worldwide held them without understanding the risk.\n3. **Too much borrowing.** Banks financed these holdings with huge amounts of short-term debt.\n\nWhen house prices stopped rising, defaults climbed, the securities lost value, and lenders stopped trusting each other. Lehman Brothers failed in September 2008, credit froze, and governments stepped in with bailouts.')]))
    C.append(AI('Debug a SQL query with a slow join', 'Explaining why a join was slow and adding an index.', (6, 3), [
        ('This query takes 40 seconds. `SELECT o.id, c.name FROM orders o JOIN customers c ON c.email = o.customer_email WHERE o.created_at > now() - interval \'7 days\'`. Table sizes: orders 12M, customers 400k.',
         'Likely culprit: you join on `email`, which probably has no index, so the database scans `customers` for each matching order. Fix in two steps:\n\n```sql\nCREATE INDEX CONCURRENTLY idx_customers_email ON customers (email);\nCREATE INDEX CONCURRENTLY idx_orders_created_at ON orders (created_at);\n```\n\nThen check the plan with `EXPLAIN (ANALYZE, BUFFERS)`; you want an index scan on `orders` and an index lookup on `customers`. Longer term, join on a numeric `customer_id` instead of an email string.')]))
    C.append(AI('Short story opening about a lighthouse keeper', 'Three opening paragraphs.', (6, 21), [
        ('Write the opening of a short story: a lighthouse keeper who finds a message in a bottle addressed to him.',
         'The bottle had been in the water so long that the label had come off, but the cork was waxed and the paper inside was dry. Anselm turned it over in the grey morning light and read his own name, written in a hand he had not seen in thirty years.\n\nHe set the kettle on before he opened it. Forty-one winters on the rock had taught him that bad news kept, and tea did not.\n\n"The light has been wrong for three nights," the letter began. "You will want to check the lens."')]))
    C.append(AI('Compare Postgres and MySQL for a small SaaS', 'Decision summary.', (7, 14), [
        ('We are a three-person team building a small B2B SaaS. Postgres or MySQL?',
         '**Postgres**, unless you have a specific reason otherwise.\n\n- Richer types (JSONB, arrays, ranges) mean fewer awkward schemas\n- Stronger constraints and transactional DDL make migrations safer\n- Excellent extensions: full-text search, `pg_trgm`, PostGIS later if you need it\n\nMySQL is a fine choice if your team knows it well or your host only offers it. At your size the deciding factor is what you can operate confidently, not benchmarks.')]))
    C.append(AI('Prepare for a behavioral interview', 'STAR stories for common questions.', (8, 5), [
        ('Help me prepare for a behavioral interview for an engineering manager role.',
         'Prepare five stories you can reshape with the STAR format (Situation, Task, Action, Result):\n\n1. A conflict inside your team and how you resolved it\n2. A project that slipped and what you changed\n3. Giving hard feedback\n4. A decision you made with incomplete information\n5. Growing someone on your team\n\nFor each, write the result as a number or a concrete change. Want to practice? Give me a story and I will play interviewer.'),
        ('Here is one: I took over a team whose releases kept failing. I introduced a release checklist and a weekly retro.',
         'Good start, but it is missing the Result and your personal contribution. Try:\n\n"Releases failed about one in three times and morale was low (situation). I was asked to stabilize them within a quarter (task). I wrote a release checklist with the team, ran a weekly 30-minute retro and made one fix each week (action). Failed releases dropped from 33% to under 5% in ten weeks, and two engineers volunteered to rotate as release lead (result)."')]))
    C.append(AI('Translate and explain a French contract clause', 'Plain-English explanation.', (8, 19), [
        ('What does "Le présent contrat est conclu pour une durée d\'un an, renouvelable par tacite reconduction" mean?',
         'It means: "This contract is made for one year and renews automatically."\n\n**Tacite reconduction** is the important part: unless one party cancels in time (check the notice period elsewhere in the contract), it renews for another term without anyone signing again. Put the notice deadline in your calendar.\n\nI am not a lawyer; for a binding interpretation ask a qualified professional.')]))
    C.append(AI('Draft a README for a small CLI', 'README written as an artifact.', (9, 2), [
        ('Draft a README for my CLI tool `stash` that keeps named directories. Subcommands: add, list, rm. Install via cargo.',
         'I wrote the README as a document you can copy. It covers installation, the three commands with examples, and the config location. Say if you want a section on shell completions.')],
        artifact=(0, 'README.md', '# stash\n\nKeep track of named directories.\n\n## Install\n\n```sh\ncargo install stash\n```\n\n## Usage\n\n```sh\nstash add notes ~/notes\nstash list\nstash rm notes\n```\n\nConfiguration lives in `~/.config/stash/config.toml`.')))
    C.append(AI('Brainstorm names for a budgeting app', 'Name ideas with reasoning.', (9, 9), [
        ('Brainstorm 10 names for a calm, minimal budgeting app.',
         'Grouped by feel:\n\n**Calm:** Stillwater, Ledgerly, Quiet Cents\n**Simple:** Tally, Penny Jar, Envelope\n**Playful:** Nickel & Dime, Pocketful, Moneybox\n**Short:** Coin\n\nMy picks: **Stillwater** (matches the calm tone) and **Tally** (short, easy to say). Check domain and trademark availability before you fall in love.')]))
    C.append(AI('Explain gradient descent to a high schooler', 'Hill-walking analogy.', (9, 16), [
        ('Explain gradient descent to a high schooler without equations.',
         'Imagine you are standing on a foggy hillside and want to reach the valley. You cannot see far, but you can feel which direction slopes downhill under your feet.\n\n1. Feel the slope where you stand.\n2. Take a small step downhill.\n3. Repeat.\n\nThe "slope" is the gradient, the step size is the learning rate, and the valley is the best settings for the model. Steps too big and you overshoot; too small and it takes forever.')]))
    C.append(AI('Write a polite email declining a meeting', 'Three tone variants.', (9, 24), [
        ('Write a polite email declining a meeting invitation. I have a conflict but want to offer an alternative.',
         '**Subject:** Re: Planning sync on Thursday\n\nHi Priya,\n\nThanks for the invite. I have a conflict on Thursday afternoon and will not be able to join. Could we move it to Friday morning, or would a short written update work instead? Happy to share notes beforehand.\n\nBest,\nAlex')]))
    mid = str(datetime(2026, 9, 28, tzinfo=timezone.utc).timestamp())
    J = lambda o: json.dumps(o, ensure_ascii=False, indent=1)
    zp = os.path.join(home, 'Downloads', 'data-6f1d2c3b-4a5e-4f60-8a7b-9c0d1e2f3a4b-1790000000-c0ffee12-batch-0000.zip')
    os.makedirs(os.path.dirname(zp), exist_ok=True); pid = U('ai-project-demo')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, o in [('users.json', [{'uuid': U('acct'), 'full_name': 'Alex Demo', 'email_address': 'alex.demo@example.com', 'verified_phone_number': None}]),
                     ('memories.json', [{'conversations_memory': 'Works on small web and CLI projects; prefers concise answers.', 'project_memories': {pid: 'Writing and planning helper.'}, 'account_uuid': U('acct')}]),
                     (f'projects/{pid}.json', {'uuid': pid, 'name': 'Writing and planning', 'description': '', 'is_private': True, 'docs': [], 'created_at': ai_ts(3, 1, 0, 0), 'updated_at': ai_ts(3, 1, 0, 0)}),
                     ('conversations.json', C)]:
            zi = zipfile.ZipInfo(n, (2026, 9, 28, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; z.writestr(zi, J(o))
    return len(C)

# ───────────── ChatGPT 导出包 ─────────────
M5 = {'model_slug': 'gpt-5'}
def GP(key, title, dt, turns, tools=None):
    """turns=[(问, 答)]；tools={k: ('code', 代码, 输出) | ('quote', url, 域名, 标题, 引文)} 插在第 k 轮问答之间"""
    mf.GT0 = dt; g = mf.GConv(key); t = 0; prev = 'root'; g.add('root', None)
    def tick(): nonlocal t; t += 1; return t
    for k, (q, a) in enumerate(turns):
        g.add(f'u{k}', prev, 'user', T_(q), tick(), status=False); prev = f'u{k}'
        if tools and k in tools:
            tl = tools[k]
            if tl[0] == 'code':
                g.add(f'c{k}', prev, 'assistant', {'content_type': 'code', 'language': 'python', 'text': tl[1]}, tick(), to='python', meta=M5)
                g.add(f'o{k}', f'c{k}', 'tool', {'content_type': 'execution_output', 'text': tl[2]}, tick(), nm='python'); prev = f'o{k}'
            else:
                g.add(f'q{k}', prev, 'tool', {'content_type': 'tether_quote', 'url': tl[1], 'domain': tl[2], 'title': tl[3], 'text': tl[4]}, tick(), nm='browser'); prev = f'q{k}'
        g.add(f'a{k}', prev, 'assistant', T_(a), tick(), meta=M5, status=False); prev = f'a{k}'
    return g.out(prev, title=title, create_time=mf.gt(0), update_time=mf.gt(t + 1))

def build_gpt(home):
    G = []
    G.append(GP('demo-g1', 'Pandas groupby cheat sheet', datetime(2026, 3, 22, 14, 5, tzinfo=timezone.utc), [
        ('Give me a short cheat sheet for pandas groupby with the patterns I will actually use.',
         'The patterns that cover most real work:\n\n```python\ndf.groupby("team")["score"].mean()                       # one aggregate\ndf.groupby("team").agg(avg=("score", "mean"), n=("id", "count"))   # named aggregates\ndf.groupby("team")["score"].transform("mean")             # broadcast back to rows\ndf.groupby(["team", "month"], as_index=False).sum()       # flat result\n```\n\nRemember `observed=True` for categoricals and `dropna=False` if you want NaN groups.')]))
    G.append(GP('demo-g2', 'Compound interest check', datetime(2026, 4, 17, 19, 30, tzinfo=timezone.utc), [
        ('If I invest 5,000 dollars at 6% a year for 20 years with annual compounding, what do I end up with? Please compute it.',
         'Computed with Python: the balance after 20 years is about **$16,035.68**, so roughly $11,036 of that is growth.\n\nFormula: `5000 * 1.06 ** 20`. Adding a yearly 1,000 deposit would bring it to about $53,000.')],
        tools={0: ('code', 'principal, rate, years = 5000, 0.06, 20\nbalance = principal * (1 + rate) ** years\nprint(round(balance, 2), round(balance - principal, 2))', '16035.68 11035.68')}))
    G.append(GP('demo-g3', 'Latest stable Python release', datetime(2026, 5, 26, 8, 15, tzinfo=timezone.utc), [
        ('What are the headline features of the newest stable Python release? Search the web.',
         'According to the official release notes, the headline items are:\n\n- Continued work on the free-threaded build, now documented as officially supported\n- Faster startup and a more capable JIT option\n- Clearer error messages for common mistakes\n\nCheck the "What\'s New" page for the full list before upgrading production services.')],
        tools={0: ('quote', 'https://docs.python.org/3/whatsnew/', 'docs.python.org', 'What\'s New in Python', 'Summary - Release highlights: improved interactive interpreter, experimental free-threaded build, experimental JIT compiler, ...')}))
    G.append(GP('demo-g4', 'Regex to match ISO dates', datetime(2026, 6, 30, 16, 40, tzinfo=timezone.utc), [
        ('Write a regex that matches ISO 8601 dates like 2026-09-30 and rejects month 13.',
         'Use:\n\n```\n^\\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])$\n```\n\nIt checks month 01 to 12 and day 01 to 31. It cannot know that February 30 is invalid, so validate the final date with your language\'s date parser as well.'),
        ('Can you also allow an optional time like T14:30:00Z?',
         'Append an optional group:\n\n```\n^\\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])(T([01]\\d|2[0-3]):[0-5]\\d:[0-5]\\d(Z|[+-]\\d{2}:\\d{2})?)?$\n```\n\nThis accepts `2026-09-30`, `2026-09-30T14:30:00Z` and `2026-09-30T14:30:00+02:00`.')]))
    G.append(GP('demo-g5', 'Ideas for a team offsite agenda', datetime(2026, 7, 21, 11, 0, tzinfo=timezone.utc), [
        ('We have a one-day offsite for 12 engineers. Suggest an agenda that is not just slides.',
         '**09:30** Coffee and a 10-minute "what surprised you this quarter" round\n**10:00** Pairs map the biggest source of friction on a whiteboard\n**11:30** Vote and pick the top three\n**12:30** Lunch away from screens\n**13:30** Three working groups draft one-page proposals\n**15:30** Each group pitches for 5 minutes, decide owners\n**16:30** Retro and a short walk\n\nThe key is to end with named owners and dates, otherwise the energy fades by Monday.')]))
    G.append(GP('demo-g6', 'Explain CORS errors', datetime(2026, 8, 19, 13, 25, tzinfo=timezone.utc), [
        ('Why do I get "blocked by CORS policy" when my React app calls my API on another port?',
         'Browsers only let a page read responses from another origin if that server opts in. `localhost:5173` and `localhost:3000` are different origins because the port differs.\n\nFix it on the server, not the client. For Express:\n\n```js\nimport cors from "cors";\napp.use(cors({ origin: "http://localhost:5173", credentials: true }));\n```\n\nIn development you can also proxy through the dev server (`server.proxy` in Vite) so the browser sees one origin.')]))
    G.append(GP('demo-g7', 'Sourdough starter troubleshooting', datetime(2026, 9, 11, 7, 50, tzinfo=timezone.utc), [
        ('My sourdough starter smells like nail polish remover and has a layer of liquid on top. Is it dead?',
         'No, it is hungry. The acetone smell and the dark liquid ("hooch") are signs it has run out of food.\n\n1. Pour off the liquid\n2. Discard all but 50 g of starter\n3. Feed it 50 g flour and 50 g water\n4. Feed twice a day for two days\n\nIf it doubles within 6 to 8 hours after a feeding, it is healthy again.')]))
    G.append(GP('demo-g8', 'Convert Celsius to Fahrenheit in bulk', datetime(2026, 9, 25, 18, 10, tzinfo=timezone.utc), [
        ('Convert these to Fahrenheit: 18, 21.5, 30, 37. Show your work with code.',
         'Results: 18 C = 64.4 F, 21.5 C = 70.7 F, 30 C = 86.0 F, 37 C = 98.6 F.\n\nThe rule is `F = C * 9/5 + 32`.')],
        tools={0: ('code', 'for c in [18, 21.5, 30, 37]:\n    print(c, round(c * 9 / 5 + 32, 1))', '18 64.4\n21.5 70.7\n30 86.0\n37 98.6')}))
    user = {'id': 'user-DEMO', 'email': 'alex.demo@example.com', 'chatgpt_plus_user': True, 'phone_number': None}
    zd = os.path.join(home, 'Downloads'); os.makedirs(zd, exist_ok=True)
    J = lambda o: json.dumps(o, ensure_ascii=False, indent=1)
    with zipfile.ZipFile(os.path.join(zd, '5b8d1f0a9c2e47d3b6a1f0e8d7c6b5a4f3e2d1c0-2026-09-30-08-00-00-4d3c2b1a.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in [('conversations.json', G), ('user.json', user), ('chat.html', b'<html><body>demo chat.html</body></html>')]:
            zi = zipfile.ZipInfo(n, (2026, 9, 30, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; z.writestr(zi, b if isinstance(b, bytes) else J(b))
    return len(G)

def main():
    if len(sys.argv) != 2: sys.exit('usage: make_demo_data.py <target-dir>')
    root = os.path.abspath(sys.argv[1]); home = os.path.join(root, 'home')
    if os.path.exists(root): shutil.rmtree(root)
    os.makedirs(home)
    ncc, nsub, nstar = build_cc(home); nai = build_ai(home); ngpt = build_gpt(home)
    cfg = {'out_dir': os.path.join(root, 'out'), 'claude_code_roots': [home + '/.claude/projects'], 'extra_backup_roots': [],
           'claude_ai_zips': [home + '/Downloads/data-*-batch-*.zip'], 'chatgpt_zips': [home + '/Downloads/*.zip'],
           'desktop_meta_globs': [home + '/desktop-meta/claude-code-sessions/**/local_*.json'],
           'redact': True, 'timezone': '+00:00'}
    json.dump(cfg, open(os.path.join(root, 'config.json'), 'w'), indent=1)
    print(f'demo data: Claude Code {ncc} sessions (+{nsub} subagents, {nstar} starred), claude.ai {nai}, ChatGPT {ngpt}')
    print(f'HOME={home} XDG_CONFIG_HOME={root}/xdg/config XDG_DATA_HOME={root}/xdg/data python3 claude_archive.py --config {root}/config.json')

if __name__ == '__main__':
    main()
