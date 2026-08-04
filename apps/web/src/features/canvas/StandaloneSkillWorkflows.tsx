import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Film,
  ImagePlay,
  Music2,
  Play,
  Sparkles,
  Upload,
  UserRound,
  WandSparkles,
  X,
} from "lucide-react";
import { SelectMenu } from "../../components/SelectMenu";

export type StandaloneWorkflowKind = "character-turnaround" | "first-frame-video" | "audio-video";

export type StandaloneWorkflowResult = {
  nodeKind: "image" | "video";
  title: string;
  description: string;
  prompt: string;
  assetName: string;
  model: string;
  aspectRatio: string;
  resolution: string;
  duration?: number;
};

type Props = {
  open: boolean;
  nodeId: string | null;
  workflow: StandaloneWorkflowKind | null;
  onClose: () => void;
  onComplete: (nodeId: string, workflow: StandaloneWorkflowKind, result: StandaloneWorkflowResult) => void;
};

type SourceMode = "upload" | "canvas" | "generate";

const WORKFLOW_META: Record<StandaloneWorkflowKind, { title: string; skill: string; steps: string[] }> = {
  "character-turnaround": {
    title: "角色三视图",
    skill: "n2d-character-turnaround",
    steps: ["选择角色图", "完善角色设定", "生成三视图"],
  },
  "first-frame-video": {
    title: "首帧图生视频",
    skill: "n2d-first-frame-video",
    steps: ["选择首帧", "设计运动", "生成视频"],
  },
  "audio-video": {
    title: "音频生视频",
    skill: "n2d-audio-video",
    steps: ["导入音频", "节拍与画面", "生成视频"],
  },
};

const VIDEO_MODELS = ["Seedance 2.0", "Lib Video 2.0", "Veo 3.1"];
const IMAGE_MODELS = ["Lib Image", "Seedream 5.0 Pro"];

function SourceTabs({ value, onChange, labels }: { value: SourceMode; onChange: (value: SourceMode) => void; labels?: Partial<Record<SourceMode, string>> }) {
  return <nav className="standalone-source-tabs" role="tablist">
    {(["upload", "canvas", "generate"] as SourceMode[]).map((mode) => <button key={mode} type="button" role="tab" aria-selected={value === mode} className={value === mode ? "is-active" : ""} onClick={() => onChange(mode)}>{labels?.[mode] ?? (mode === "upload" ? "本地上传" : mode === "canvas" ? "从当前画布选择" : "AI 生成")}</button>)}
  </nav>;
}

function WorkflowHeader({ workflow, step, completed, onStep, onClose }: { workflow: StandaloneWorkflowKind; step: number; completed: number; onStep: (step: number) => void; onClose: () => void }) {
  const meta = WORKFLOW_META[workflow];
  return <header className="standalone-workflow-topbar">
    <div className="standalone-workflow-brand">
      <span>{workflow === "character-turnaround" ? <UserRound size={17} /> : workflow === "first-frame-video" ? <ImagePlay size={17} /> : <Music2 size={17} />}</span>
      <div><strong>{meta.title}</strong><small>Skill · {meta.skill}</small></div>
    </div>
    <nav aria-label={`${meta.title}步骤`}>
      {meta.steps.map((label, index) => {
        const number = index + 1;
        const done = number <= completed;
        return <span key={label}><button type="button" className={`${step === number ? "is-active" : ""}${done ? " is-done" : ""}`} onClick={() => onStep(number)}><i>{done && step !== number ? <Check size={12} /> : number}</i><b>{label}</b></button>{number < meta.steps.length && <em />}</span>;
      })}
    </nav>
    <button type="button" aria-label={`关闭${meta.title}`} title="关闭 (ESC)" onClick={onClose}><X size={18} /></button>
  </header>;
}

function OptionSelect({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  return <div className="standalone-select"><span>{label}</span><SelectMenu ariaLabel={label} value={value} options={values.map((item) => ({ value: item, label: item }))} onChange={onChange} /></div>;
}

function CharacterTurnaroundFlow({ step, setStep, onComplete }: { step: number; setStep: (step: number) => void; onComplete: (result: StandaloneWorkflowResult) => void }) {
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload");
  const [sourceName, setSourceName] = useState("");
  const [name, setName] = useState("未命名角色");
  const [face, setFace] = useState("清晰脸型与稳定五官比例，正视中性表情");
  const [hair, setHair] = useState("发型、发色、发际线保持一致");
  const [body, setBody] = useState("自然直立，身体比例与体型保持一致");
  const [outfit, setOutfit] = useState("同一套服装、鞋履和配饰，结构与配色不变");
  const [model, setModel] = useState(IMAGE_MODELS[0]);
  const [resolution, setResolution] = useState("2K");
  const [ratio, setRatio] = useState("16:9");
  const [generation, setGeneration] = useState<"idle" | "running" | "done">("idle");
  const sourceReady = Boolean(sourceName);
  const identityReady = [name, face, hair, body, outfit].every((value) => value.trim());
  const prompt = `${name}角色设定三视图，正面、左侧面、背面，全身自然直立。${face}；${hair}；${body}；${outfit}。纯中性浅灰背景，三视图等比例排列，禁止服装、发型、脸型和体型变化，无文字无水印。`;

  const chooseCanvas = () => setSourceName("画布角色参考图");
  const chooseGenerated = () => setSourceName("AI 角色候选图");
  const generate = () => {
    if (!sourceReady || !identityReady || generation === "running") return;
    setGeneration("running");
    window.setTimeout(() => setGeneration("done"), 900);
  };

  return <>
    {step === 1 && <main className="standalone-workflow-body source-step">
      <section className="standalone-workflow-copy"><small>STEP 01</small><h1>先选一张稳定的角色主参考</h1><p>三视图会严格继承这张图的脸型、发型、服装和身体比例。请优先选择主体完整、无遮挡的单人图。</p><ul><li>建议正面或四分之三正面</li><li>避免多人同框与重度滤镜</li><li>占位缩略图不会被当作真实参考</li></ul></section>
      <section className="standalone-source-panel"><SourceTabs value={sourceMode} onChange={setSourceMode} />
        {sourceMode === "upload" ? <label className={`standalone-dropzone${sourceReady ? " is-ready" : ""}`}><input type="file" accept="image/*" onChange={(event) => setSourceName(event.target.files?.[0]?.name ?? "")} />{sourceReady ? <><Check size={28} /><strong>{sourceName}</strong><small>已绑定为角色主参考</small></> : <><Upload size={30} /><strong>拖拽角色图片到这里，或点击上传</strong><small>支持 PNG、JPG、WEBP · 建议单人全身图</small></>}</label>
          : sourceMode === "canvas" ? <div className="standalone-canvas-picks"><button type="button" onClick={chooseCanvas}><span className="pick-character"><UserRound size={38} /></span><b>角色图</b><small>当前画布 · 最近使用</small></button><button type="button" onClick={chooseCanvas}><span className="pick-character alt"><UserRound size={38} /></span><b>角色参考</b><small>当前画布 · 角色资产</small></button></div>
            : <div className="standalone-generate-source"><WandSparkles size={35} /><strong>先生成一张角色主参考</strong><textarea aria-label="角色主参考描述" defaultValue="电影感角色全身立绘，正面站立，脸部清晰，服装完整，纯净背景" /><button type="button" onClick={chooseGenerated}><Sparkles size={14} />生成参考候选</button></div>}
      </section>
      <footer><span>{sourceReady ? <><Check size={13} />已选择：{sourceName}</> : "请选择角色主参考后继续"}</span><button type="button" className="primary" disabled={!sourceReady} onClick={() => setStep(2)}>下一步：完善角色设定 <ArrowRight size={14} /></button></footer>
    </main>}
    {step === 2 && <main className="standalone-workflow-body form-step">
      <section className="standalone-form-card"><header><small>IDENTITY BRIEF</small><h2>锁定角色不可漂移的身份事实</h2><p>这些字段会同时进入三个视角，不会把“保持一致”当作唯一约束。</p></header>
        <label><span>角色名称</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="standalone-form-grid"><label><span>脸型与五官</span><textarea value={face} onChange={(event) => setFace(event.target.value)} /></label><label><span>发型与发色</span><textarea value={hair} onChange={(event) => setHair(event.target.value)} /></label><label><span>体型与比例</span><textarea value={body} onChange={(event) => setBody(event.target.value)} /></label><label><span>服装与配饰</span><textarea value={outfit} onChange={(event) => setOutfit(event.target.value)} /></label></div>
      </section>
      <aside className="standalone-contract-preview"><strong>一致性约束预览</strong><div><span>FACE</span><p>{face}</p></div><div><span>HAIR</span><p>{hair}</p></div><div><span>BODY</span><p>{body}</p></div><div><span>OUTFIT</span><p>{outfit}</p></div></aside>
      <footer><button type="button" onClick={() => setStep(1)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={!identityReady} onClick={() => setStep(3)}>下一步：生成三视图 <ArrowRight size={14} /></button></footer>
    </main>}
    {step === 3 && <main className="standalone-workflow-body generate-step">
      <section className="standalone-generation-preview character-sheet"><header><span>角色三视图预览</span><small>{generation === "done" ? "3/3 已生成" : generation === "running" ? "正在生成…" : "等待生成"}</small></header><div>{["正面", "左侧面", "背面"].map((label, index) => <article key={label} className={generation === "done" ? "is-ready" : ""}><span className={`turnaround-figure figure-${index}`}><i /><b /><em /></span><strong>{label}</strong><small>{generation === "done" ? "身份一致性待人工验收" : "保持站姿与比例一致"}</small></article>)}</div></section>
      <aside className="standalone-generation-settings"><h3>生成设置</h3><OptionSelect label="模型" value={model} values={IMAGE_MODELS} onChange={setModel} /><OptionSelect label="画面比例" value={ratio} values={["16:9", "3:2", "2:1"]} onChange={setRatio} /><OptionSelect label="分辨率" value={resolution} values={["2K", "4K"]} onChange={setResolution} /><label><span>三视图提示词</span><textarea value={prompt} readOnly /></label><small>实际付费后端接入后，提交前会再次确认。</small><button type="button" className="primary" disabled={generation === "running"} onClick={generate}>{generation === "running" ? <><span className="standalone-spinner" />生成中</> : generation === "done" ? <><Sparkles size={14} />重新生成</> : <><Sparkles size={14} />生成三视图</>}</button></aside>
      <footer><button type="button" onClick={() => setStep(2)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={generation !== "done"} onClick={() => onComplete({ nodeKind: "image", title: `${name} · 角色三视图`, description: "正面、左侧面与背面一致性角色设定图", prompt, assetName: "角色三视图/turnaround.png", model, aspectRatio: ratio, resolution })}><Check size={14} />验收并发送到画布</button></footer>
    </main>}
  </>;
}

function FirstFrameVideoFlow({ step, setStep, onComplete }: { step: number; setStep: (step: number) => void; onComplete: (result: StandaloneWorkflowResult) => void }) {
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload");
  const [sourceName, setSourceName] = useState("");
  const [subject, setSubject] = useState("主体缓慢抬头并转向镜头，衣物与发丝有轻微自然摆动");
  const [camera, setCamera] = useState("缓慢推进");
  const [environment, setEnvironment] = useState("背景光影自然流动，空间结构保持不变");
  const [pacing, setPacing] = useState("前2秒建立氛围，中段完成动作，结尾稳定停留");
  const [model, setModel] = useState(VIDEO_MODELS[0]);
  const [resolution, setResolution] = useState("720P");
  const [ratio, setRatio] = useState("16:9");
  const [duration, setDuration] = useState("5");
  const [generation, setGeneration] = useState<"idle" | "running" | "done">("idle");
  const sourceReady = Boolean(sourceName);
  const motionReady = [subject, camera, environment, pacing].every((value) => value.trim());
  const prompt = `以输入首帧为第0帧并保持构图连续。主体运动：${subject}。镜头运动：${camera}。环境变化：${environment}。节奏：${pacing}。禁止身份改变、服装改变、肢体变形、背景重绘和首帧跳切。`;
  const chooseSource = (name: string) => setSourceName(name);
  const generate = () => { if (!sourceReady || !motionReady || generation === "running") return; setGeneration("running"); window.setTimeout(() => setGeneration("done"), 1000); };

  return <>
    {step === 1 && <main className="standalone-workflow-body source-step"><section className="standalone-workflow-copy"><small>STEP 01</small><h1>选择视频真正的第 0 帧</h1><p>视频必须从这张图自然开始。首帧会绑定到任务中，后续更换图片会自动使旧任务失效。</p><ul><li>主体、构图与背景要清楚</li><li>避免运动模糊和遮挡</li><li>不要用占位图代替真实首帧</li></ul></section><section className="standalone-source-panel"><SourceTabs value={sourceMode} onChange={setSourceMode} />{sourceMode === "upload" ? <label className={`standalone-dropzone${sourceReady ? " is-ready" : ""}`}><input type="file" accept="image/*" onChange={(event) => chooseSource(event.target.files?.[0]?.name ?? "")} />{sourceReady ? <><Check size={28} /><strong>{sourceName}</strong><small>已绑定为视频首帧</small></> : <><Upload size={30} /><strong>拖拽首帧图片到这里，或点击上传</strong><small>支持 PNG、JPG、WEBP</small></>}</label> : sourceMode === "canvas" ? <div className="standalone-canvas-picks"><button type="button" onClick={() => chooseSource("画布图片 · 角色近景")}><span className="pick-frame"><ImagePlay size={34} /></span><b>角色近景</b><small>当前画布</small></button><button type="button" onClick={() => chooseSource("画布图片 · 场景全景")}><span className="pick-frame alt"><ImagePlay size={34} /></span><b>场景全景</b><small>当前画布</small></button></div> : <div className="standalone-generate-source"><WandSparkles size={35} /><strong>先生成一张视频首帧</strong><textarea aria-label="首帧画面描述" defaultValue="电影感画面，主体清晰，动作即将发生，环境层次完整" /><button type="button" onClick={() => chooseSource("AI 首帧候选图")}><Sparkles size={14} />生成首帧候选</button></div>}</section><footer><span>{sourceReady ? <><Check size={13} />已选择：{sourceName}</> : "请选择真实首帧后继续"}</span><button type="button" className="primary" disabled={!sourceReady} onClick={() => setStep(2)}>下一步：设计运动 <ArrowRight size={14} /></button></footer></main>}
    {step === 2 && <main className="standalone-workflow-body motion-step"><section className="standalone-motion-preview"><div className="motion-frame"><ImagePlay size={48} /><span>首帧</span><i className={`camera-${camera === "缓慢推进" ? "push" : camera === "向右横移" ? "pan" : "orbit"}`} /></div><div className="motion-timeline"><span><i />0s</span><b /><span><i />{duration}s</span></div><small>{sourceName}</small></section><section className="standalone-form-card"><header><small>MOTION DESIGN</small><h2>把静态画面拆成三层运动</h2></header><label><span>主体动作</span><textarea value={subject} onChange={(event) => setSubject(event.target.value)} /></label><label><span>镜头运动</span><div className="standalone-choice-row">{["缓慢推进", "向右横移", "轻微环绕"].map((value) => <button type="button" key={value} className={camera === value ? "is-active" : ""} onClick={() => setCamera(value)}>{value}</button>)}</div></label><label><span>环境变化</span><textarea value={environment} onChange={(event) => setEnvironment(event.target.value)} /></label><label><span>节奏</span><textarea value={pacing} onChange={(event) => setPacing(event.target.value)} /></label></section><footer><button type="button" onClick={() => setStep(1)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={!motionReady} onClick={() => setStep(3)}>下一步：生成视频 <ArrowRight size={14} /></button></footer></main>}
    {step === 3 && <main className="standalone-workflow-body generate-step"><section className={`standalone-generation-preview video-result${generation === "done" ? " is-ready" : ""}`}><header><span>视频预览</span><small>{generation === "done" ? "已生成 · 待人工验收" : generation === "running" ? "正在延展首帧…" : "等待生成"}</small></header><div><span className="video-result-frame"><ImagePlay size={54} /><i>{generation === "done" ? <Play size={22} fill="currentColor" /> : <Film size={22} />}</i></span><b>{sourceName}</b><small>{duration}s · {ratio} · {resolution}</small></div></section><aside className="standalone-generation-settings"><h3>生成设置</h3><OptionSelect label="视频模型" value={model} values={VIDEO_MODELS} onChange={setModel} /><OptionSelect label="画面比例" value={ratio} values={["16:9", "9:16", "1:1"]} onChange={setRatio} /><OptionSelect label="清晰度" value={resolution} values={["720P", "1080P"]} onChange={setResolution} /><OptionSelect label="时长" value={duration} values={["5", "8", "10"]} onChange={setDuration} /><label><span>最终运动提示词</span><textarea value={prompt} readOnly /></label><small>真实生成会在提交前确认预计积分与模型。</small><button type="button" className="primary" disabled={generation === "running"} onClick={generate}>{generation === "running" ? <><span className="standalone-spinner" />生成中</> : generation === "done" ? <><Sparkles size={14} />重新生成</> : <><ImagePlay size={14} />生成视频</>}</button></aside><footer><button type="button" onClick={() => setStep(2)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={generation !== "done"} onClick={() => onComplete({ nodeKind: "video", title: "首帧图生视频结果", description: "基于已绑定首帧生成的连续动作视频", prompt, assetName: "出视频/first-frame-video.mp4", model, aspectRatio: ratio, resolution, duration: Number(duration) })}><Check size={14} />验收并发送到画布</button></footer></main>}
  </>;
}

function AudioVideoFlow({ step, setStep, onComplete }: { step: number; setStep: (step: number) => void; onComplete: (result: StandaloneWorkflowResult) => void }) {
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload");
  const [audioName, setAudioName] = useState("");
  const [duration, setDuration] = useState(32);
  const [analysis, setAnalysis] = useState(false);
  const [style, setStyle] = useState("电影感写实，冷暖光影随音乐能量逐段增强");
  const [subject, setSubject] = useState("同一主角在城市夜景中前行，人物身份与服装持续一致");
  const [camera, setCamera] = useState("低能量段缓慢推进，高能量段在强拍切换景别并加入环绕");
  const [cutStrength, setCutStrength] = useState(62);
  const [model, setModel] = useState(VIDEO_MODELS[0]);
  const [resolution, setResolution] = useState("720P");
  const [ratio, setRatio] = useState("16:9");
  const [generation, setGeneration] = useState<"idle" | "running" | "done">("idle");
  const timeline = useMemo(() => [
    { label: "前奏", start: 0, end: 8, energy: "低", width: 24 },
    { label: "主歌", start: 8, end: 20, energy: "中", width: 38 },
    { label: "副歌", start: 20, end: duration, energy: "高", width: 38 },
  ], [duration]);
  const audioReady = Boolean(audioName);
  const planReady = analysis && [style, subject, camera].every((value) => value.trim());
  const prompt = `视觉风格：${style}。主体连续：${subject}。运镜与剪辑：${camera}。切镜强度 ${cutStrength}%。按前奏、主歌、副歌的能量与强拍执行卡点，禁止主体随机变化、无节奏跳切、画面闪烁和音轨截断。`;
  const selectAudio = (name: string, seconds = 32) => { setAudioName(name); setDuration(seconds); setAnalysis(false); };
  const generate = () => { if (!planReady || generation === "running") return; setGeneration("running"); window.setTimeout(() => setGeneration("done"), 1100); };

  return <>
    {step === 1 && <main className="standalone-workflow-body source-step"><section className="standalone-workflow-copy"><small>STEP 01</small><h1>导入要驱动画面的完整音频</h1><p>工作台会先锁定音频文件，再建立可编辑的段落与卡点时间线。替换音频后，旧时间线和生成任务会失效。</p><ul><li>推荐 WAV、MP3、M4A</li><li>保留完整音频作为最终时间基准</li><li>未读取真实时长时不会伪装分析完成</li></ul></section><section className="standalone-source-panel"><SourceTabs value={sourceMode} onChange={setSourceMode} labels={{ canvas: "从当前画布选择", generate: "使用示例音频" }} />{sourceMode === "upload" ? <label className={`standalone-dropzone audio${audioReady ? " is-ready" : ""}`}><input type="file" accept="audio/*" onChange={(event) => selectAudio(event.target.files?.[0]?.name ?? "", 32)} />{audioReady ? <><Check size={28} /><strong>{audioName}</strong><small>已绑定 · 预计 {duration}s</small></> : <><Upload size={30} /><strong>拖拽音频到这里，或点击上传</strong><small>支持 WAV、MP3、M4A</small></>}</label> : sourceMode === "canvas" ? <div className="standalone-audio-picks"><button type="button" onClick={() => selectAudio("画布音频 · 夜色序曲.wav", 32)}><span className="audio-wave">{[8, 17, 12, 24, 14, 20, 10, 16].map((height, index) => <i key={index} style={{ height }} />)}</span><b>夜色序曲.wav</b><small>00:32 · 当前画布</small></button><button type="button" onClick={() => selectAudio("画布音频 · 史诗鼓点.mp3", 45)}><span className="audio-wave alt">{[16, 8, 22, 12, 25, 13, 20, 9].map((height, index) => <i key={index} style={{ height }} />)}</span><b>史诗鼓点.mp3</b><small>00:45 · 当前画布</small></button></div> : <div className="standalone-generate-source"><Music2 size={35} /><strong>使用示例音频体验完整流程</strong><p>32 秒、三段能量结构的演示音频，不会产生真实付费生成。</p><button type="button" onClick={() => selectAudio("示例音频 · 城市夜行.wav", 32)}><Play size={14} />使用示例音频</button></div>}</section><footer><span>{audioReady ? <><Check size={13} />已选择：{audioName}</> : "请选择音频后继续"}</span><button type="button" className="primary" disabled={!audioReady} onClick={() => { setAnalysis(true); setStep(2); }}>分析节拍与段落 <ArrowRight size={14} /></button></footer></main>}
    {step === 2 && <main className="standalone-workflow-body audio-plan-step"><section className="standalone-audio-timeline"><header><span><Music2 size={15} /><b>{audioName}</b></span><small>00:{String(duration).padStart(2, "0")} · 分析结果可编辑</small></header><div className="timeline-wave">{Array.from({ length: 72 }).map((_, index) => <i key={index} style={{ height: `${18 + ((index * 17) % 48)}%` }} />)}</div><div className="timeline-segments">{timeline.map((segment) => <button type="button" key={segment.label} style={{ width: `${segment.width}%` }}><b>{segment.label}</b><small>{segment.start}s–{segment.end}s · 能量{segment.energy}</small></button>)}</div></section><section className="standalone-form-card"><header><small>BEAT & VISUAL PLAN</small><h2>让段落变化真正驱动画面</h2></header><label><span>视觉风格</span><textarea value={style} onChange={(event) => setStyle(event.target.value)} /></label><label><span>主体连续性</span><textarea value={subject} onChange={(event) => setSubject(event.target.value)} /></label><label><span>运镜与切镜</span><textarea value={camera} onChange={(event) => setCamera(event.target.value)} /></label><label className="standalone-range"><span>切镜强度 <b>{cutStrength}%</b></span><input type="range" min="20" max="100" value={cutStrength} onChange={(event) => setCutStrength(Number(event.target.value))} /></label></section><footer><button type="button" onClick={() => setStep(1)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={!planReady} onClick={() => setStep(3)}>下一步：生成视频 <ArrowRight size={14} /></button></footer></main>}
    {step === 3 && <main className="standalone-workflow-body generate-step"><section className={`standalone-generation-preview audio-video-result${generation === "done" ? " is-ready" : ""}`}><header><span>音频卡点视频预览</span><small>{generation === "done" ? "已生成 · 待人工验收" : generation === "running" ? "正在按节拍生成…" : "等待生成"}</small></header><div className="audio-video-frames">{timeline.map((segment, index) => <span key={segment.label} className={`frame-${index}`}><i>{segment.label}</i><b>{segment.energy}能量</b></span>)}</div><div className="audio-video-playline"><Play size={16} fill="currentColor" /><span><i /></span><time>00:00 / 00:{String(duration).padStart(2, "0")}</time></div></section><aside className="standalone-generation-settings"><h3>生成设置</h3><OptionSelect label="视频模型" value={model} values={VIDEO_MODELS} onChange={setModel} /><OptionSelect label="画面比例" value={ratio} values={["16:9", "9:16", "1:1"]} onChange={setRatio} /><OptionSelect label="清晰度" value={resolution} values={["720P", "1080P"]} onChange={setResolution} /><label><span>最终音画提示词</span><textarea value={prompt} readOnly /></label><small>会保留完整原音频；真实付费提交前再次确认。</small><button type="button" className="primary" disabled={generation === "running"} onClick={generate}>{generation === "running" ? <><span className="standalone-spinner" />生成中</> : generation === "done" ? <><Sparkles size={14} />重新生成</> : <><Music2 size={14} />生成卡点视频</>}</button></aside><footer><button type="button" onClick={() => setStep(2)}><ArrowLeft size={14} />上一步</button><button type="button" className="primary" disabled={generation !== "done"} onClick={() => onComplete({ nodeKind: "video", title: "音频生视频结果", description: `根据 ${audioName} 的节拍与段落生成的连续视频`, prompt, assetName: "出视频/audio-video.mp4", model, aspectRatio: ratio, resolution, duration })}><Check size={14} />验收并发送到画布</button></footer></main>}
  </>;
}

export function StandaloneSkillWorkflowOverlay({ open, nodeId, workflow, onClose, onComplete }: Props) {
  const [step, setStep] = useState(1);
  const [sessionKey, setSessionKey] = useState("");

  useEffect(() => {
    const key = `${workflow ?? ""}:${nodeId ?? ""}`;
    if (!open || !nodeId || !workflow || key === sessionKey) return;
    setSessionKey(key);
    setStep(1);
  }, [nodeId, open, sessionKey, workflow]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open || !nodeId || !workflow) return null;
  const completed = step === 1 ? 0 : step - 1;
  const finish = (result: StandaloneWorkflowResult) => onComplete(nodeId, workflow, result);

  return <section className={`standalone-workflow-overlay workflow-${workflow}`} role="dialog" aria-modal="true" aria-label={WORKFLOW_META[workflow].title}>
    <WorkflowHeader workflow={workflow} step={step} completed={completed} onStep={setStep} onClose={onClose} />
    {workflow === "character-turnaround" ? <CharacterTurnaroundFlow key={sessionKey} step={step} setStep={setStep} onComplete={finish} /> : workflow === "first-frame-video" ? <FirstFrameVideoFlow key={sessionKey} step={step} setStep={setStep} onComplete={finish} /> : <AudioVideoFlow key={sessionKey} step={step} setStep={setStep} onComplete={finish} />}
  </section>;
}
