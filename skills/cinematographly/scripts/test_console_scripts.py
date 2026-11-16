#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""test_console_scripts.py — the two Resolve scripts, EXECUTED against a fake Resolve.

run_tests.py only compiles render-mp4.py and resolve-production-console.py, because both need
Resolve's injected `resolve`. Compiling proves nothing about what they do, and since 2026-09-14 both
run two ways: pasted into Workspace ▸ Console, or sent through the `run_script` tool of the MCP
server that ships inside Resolve Studio 21.1 — whose sandbox has no `os` and no `open`. This runs each
script in both environments against an in-memory fake that records every call, and asserts the
behaviour the skill depends on.

What it cannot prove: that Resolve behaves like the fake. The facts the fake encodes were measured
live on Studio 21.1.0.14 and are dated in references/editing-and-audio.md (§ Automating DaVinci
Resolve). Re-measure there when Resolve changes; update the fake from the measurement, never the
other way round.

  python3 test_console_scripts.py      # exit 0 all green · 1 failures
"""
from __future__ import annotations
import builtins, contextlib, io, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RENDER = os.path.join(HERE, "render-mp4.py")
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
# the imports the run_script sandbox refuses, read from the shipped server (2026-09-14)
SANDBOX_BLOCKED = {"os", "sys", "subprocess", "socket", "ctypes", "pathlib", "shutil", "importlib",
                   "multiprocessing", "_thread", "signal", "gc", "runpy", "traceback", "linecache"}
fails: list[str] = []


def check(name: str, cond: bool, detail="") -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + ("" if cond else f"\n        {str(detail)[:3000]}"))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------------------------------------------
# the fake — only what the two scripts call, behaving as measured
# ---------------------------------------------------------------------------------------------------
INSTALLED_LUTS = {"MCP/cine_kling3_0_norm_v1.cube", "MCP/cine_phone_60.cube"}   # what the fake's LUT list holds
TEMPLATES = {"/grades/clip-template.drx": ["shot_match", "deflicker", "look", "texture"],
             "/grades/timeline-template.drx": ["vignette", "film_look"]}


class Graph:
    """Measured 2026-10-26 on Studio 21.1.1 (an accessories brand's ad job): a timeline with no timeline grade has 0 nodes;
    a graded node lists its tools ("Primary Balance", "LUT: <name>"); an unlabelled node's label is '';
    GetLUT returns the path relative to the LUT folder ('MCP/…')."""
    def __init__(self, calls, nodes=1, tools=None, labels=None):
        self.calls = calls
        self.labels = list(labels or [""] * nodes)
        n = len(self.labels)
        self.tools = [list(t) for t in (tools or [[] for _ in range(n)])]
        self.luts, self.enabled = [""] * n, [True] * n

    def GetNumNodes(self): return len(self.labels)
    def GetNodeLabel(self, i): return self.labels[i - 1]
    def GetToolsInNode(self, i): return list(self.tools[i - 1])
    def GetLUT(self, i): return self.luts[i - 1]

    def SetLUT(self, i, path):
        self.calls.append(("SetLUT", i, path))
        if not 1 <= i <= len(self.labels) or path not in INSTALLED_LUTS:
            return False
        self.luts[i - 1] = path
        return True

    def SetNodeEnabled(self, i, on):
        self.calls.append(("SetNodeEnabled", i, on))
        if not 1 <= i <= len(self.labels):
            return False
        self.enabled[i - 1] = bool(on)
        return True

    def ApplyGradeFromDRX(self, path, mode, all_layers=False):
        self.calls.append(("ApplyGradeFromDRX", path, mode))
        if path not in TEMPLATES:
            return False
        n = len(TEMPLATES[path])               # a still REPLACES the graph: the template's labelled nodes
        self.labels, self.tools = list(TEMPLATES[path]), [["Primary Balance"] for _ in range(n)]
        self.luts, self.enabled = [""] * n, [True] * n
        return True


class ColorGroup:
    def __init__(self, calls, name):
        self.name, self.pre, self.post = name, Graph(calls), Graph(calls)

    def GetName(self): return self.name
    def GetPreClipNodeGraph(self): return self.pre
    def GetPostClipNodeGraph(self): return self.post


class MediaPoolItem:
    def __init__(self, file_name, title=None, srt=None, path=None):
        self.file_name, self.title, self.srt, self.path = file_name, title, srt, path
    def GetName(self): return self.file_name

    def GetClipProperty(self, key):
        if key == "Type":
            return "Subtitle" if self.srt else ("Fusion Title" if self.title else "Video")
        if key == "File Path":
            return self.path                      # a title's pool item has no file: None
        return self.file_name if key == "File Name" else None


class Folder:
    """A media pool bin: the styled title templates an editor dragged into the pool (AutoSubs' method)."""
    def __init__(self, clips, subs=()): self.clips, self.subs = list(clips), list(subs)
    def GetClipList(self): return list(self.clips)
    def GetSubFolderList(self): return list(self.subs)


def _srt_cues(path):
    """The fake's reading of an .srt — what Resolve would put on a subtitle track (not measured live: a probe)."""
    out = []
    for b in re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", b)
        if m:
            g = [int(x) for x in m.groups()]
            out.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                        " ".join(b.split("\n")[2:])))
    return out


class Item:
    def __init__(self, name, start, dur, kind="video", graph=None, file_name=None, calls=None, path=None):
        self.name, self.start, self.dur, self.kind = name, start, dur, kind
        self.graph, self.group, self.cdl, self.calls = graph, None, None, calls if calls is not None else []
        self.mpi = MediaPoolItem(file_name or name, path=path)
        self.effects = []

    def GetName(self): return self.name

    def SetName(self, n):
        self.calls.append(("SetName", self.name, n))
        self.name = n
        return True

    # ⚡ v2.45 — the installed library: effects and transitions (21.1.2 stubs; not measured live)
    def AddEffect(self, category, eid):
        self.calls.append(("AddEffect", self.name, category, eid))
        if eid not in EFFECTS_INSTALLED:
            return None
        e = FakeEffect(category, eid)
        self.effects.append(e)
        return e

    def GetEffects(self, category): return [e for e in self.effects if e.category == category]

    def AddTransition(self, opts):
        self.calls.append(("AddTransition", self.name, dict(opts)))
        tl = getattr(self, "tl", None)
        if tl is None or opts.get("type") not in TRANSITIONS_INSTALLED:
            return None
        d = int(opts.get("duration") or 12)
        cut = self.start + self.dur if opts.get("position", "end") == "end" else self.start
        key = next(k for k, v in tl.items.items() if self in v)
        if getattr(tl, "no_handles", False):        # [stub] what a cut with no handle does: here it eats frames
            for x in tl.items[key]:
                if x.start == cut:
                    x.start += d // 2
                    x.dur -= d // 2
        tr = Item(opts["type"], cut - d // 2, d, "transition")
        tl.items[key].append(tr)
        return tr
    def GetStart(self): return self.start
    def GetDuration(self): return self.dur
    def GetType(self): return self.kind
    def GetClipColor(self): return getattr(self, "color", "")

    def SetClipColor(self, c):
        self.calls.append(("SetClipColor", self.name, c))
        self.color = c
        return True
    def GetNodeGraph(self, layer=None): return self.graph
    def GetColorGroup(self): return self.group
    def GetMediaPoolItem(self): return self.mpi

    def AssignToColorGroup(self, g):
        self.calls.append(("AssignToColorGroup", self.name, g.GetName()))
        self.group = g
        return True

    def SetCDL(self, d):
        self.calls.append(("SetCDL", self.name, dict(d)))
        ok = all(isinstance(v, str) for v in d.values()) and set(d) == {"NodeIndex", "Slope", "Offset", "Power",
                                                                        "Saturation"}
        if ok:
            self.cdl = dict(d)
        return ok


# Fusion title templates the fake knows: {name: {tool name: its inputs}}. "Text+" is one TextPlus tool;
# the marketplace one hides its text behind a macro with no StyledText input of its own.
TEXTPLUS = {"StyledText": "Custom Title", "Font": "Open Sans", "Style": "Bold", "Size": 0.08,
            "HorizontalLeftCenterRight": 0, "HorizontalJustificationNew": 1, "Center": {1: 0.5, 2: 0.5},
            "Red1": 1.0, "Green1": 1.0, "Blue1": 1.0, "Enabled3": 0, "ElementShape3": 0, "Offset3": {1: 0.01, 2: -0.01},
            "Level3": 0, "Red3": 0.0, "Green3": 0.0, "Blue3": 0.0, "Alpha3": 1.0}
FUSION_TITLES = {"Text+": {"Template": TEXTPLUS},
                 "Cinematic Title 07": {"Macro1": {"Input1": 0.5}, "Background1": {"TopLeftRed": 0.0}}}


class FakeInput:
    def __init__(self, tool, key): self.tool, self.key = tool, key
    def GetExpression(self): return self.tool.exprs.get(self.key) or ""


class FusionTool:
    def __init__(self, name, inputs, regid=None, data=None, exprs=None):
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "inputs", json.loads(json.dumps(inputs)))
        object.__setattr__(self, "regid", regid)
        object.__setattr__(self, "data", dict(data or {}))
        object.__setattr__(self, "exprs", dict(exprs or {}))
        for k, v in list(self.inputs.items()):           # a point input comes back keyed 1 and 2, like Fusion's table
            if isinstance(v, dict):
                self.inputs[k] = {int(a): b for a, b in v.items()}
            elif isinstance(v, list) and len(v) == 2:
                self.inputs[k] = {1: v[0], 2: v[1]}

    def __setattr__(self, key, value):                    # tool.StyledText = text, as Fusion takes it
        if key in self.inputs:
            self.inputs[key] = value
        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, key):                           # tool.SourceTime → the input (GetExpression)
        if key in ("inputs", "exprs", "data", "regid", "Name"):
            raise AttributeError(key)
        if key in self.inputs or key in self.exprs:
            return FakeInput(self, key)
        raise AttributeError(key)
    def GetInput(self, key, time=None): return self.inputs.get(key)
    def GetData(self, name=None): return self.data.get(name) if name else dict(self.data)
    def SetInput(self, key, value, time=None):
        if key in self.inputs:
            self.inputs[key] = value          # the stub: returns None, so only a read-back proves it


class FusionComp:
    def __init__(self, tools, item=None):
        self.tools = {}
        for i, (n, v) in enumerate(tools.items()):
            self.tools[i + 1] = v if isinstance(v, FusionTool) else FusionTool(n, v)
        self.locks, self.lock_calls, self.item = 0, 0, item

    def Lock(self):
        self.locks += 1
        self.lock_calls += 1
    def Unlock(self): self.locks -= 1
    def GetToolList(self, selected=False, regid=None):
        # by registry id, as Fusion filters: a generated tool knows its own; a stock one counts as TextPlus when it
        # takes StyledText
        return {k: t for k, t in self.tools.items()
                if regid is None or (t.regid == regid if t.regid else (regid == "TextPlus" and "StyledText" in t.inputs))}
    def FindTool(self, name): return next((t for t in self.tools.values() if t.Name == name), None)

    def GetAttrs(self, key=None):
        n = self.item.dur if self.item is not None else 120
        a = {"COMPN_RenderStart": 0, "COMPN_RenderEnd": n - 1 + getattr(self, "end_skew", 0)}  # [stub: L1-d measures it]
        return a.get(key) if key else a


def comp_from_lua(text, item=None):
    """A generated .setting or .comp read with fusion_titles' own parser → the fake's comp: the tool names, registry
    ids, inputs, expressions and CustomData exactly as the generator wrote them."""
    import fusion_titles as FT
    d = FT.parse_lua(text)
    if d.get("__type") == "Composition":
        tools = d["Tools"]
    else:
        mac = next(v for k, v in d["Tools"].items() if isinstance(v, dict) and v.get("__type") == "MacroOperator")
        tools = mac["Tools"]
    out = {}
    for name, t in tools.items():
        if not isinstance(t, dict) or name == "__type" or t.get("__type") in ("BezierSpline", "XYPath"):
            continue
        ins, ex = {}, {}
        for k, v in (t.get("Inputs") or {}).items():
            if k == "__type" or not isinstance(v, dict):
                continue
            if "Expression" in v:
                ex[k] = v["Expression"]
            ins[k] = v.get("Value") if "Value" in v else None
        if t.get("__type") == "TextPlus":
            ins = {**TEXTPLUS, **{k: v for k, v in ins.items() if v is not None}}     # every Text+ has all its inputs
        out[name] = FusionTool(name, ins, regid=t.get("__type"), data=t.get("CustomData") or {}, exprs=ex)
    return FusionComp(out, item)


INSTALLED = {}            # name → .setting text: templates a fake fusion.InstallFile has registered
EFFECTS_INSTALLED = {"Fusion/Effects/Krokodove/Bevel", "Open FX/MrAlexTech/MagicAnimate Free",
                     "Fusion/Effects/Video Editor Studio/Continuous Zoom"}
TRANSITIONS_INSTALLED = {"Cross Dissolve", "Smooth Zoom In"}


class FakeEffect:
    def __init__(self, category, eid):
        self.category, self.eid = category, eid
        self.comp = FusionComp({"Zoom": {"Size": 1.0, "Angle": 0.0}}) if category == "fusion" else None
    def GetInfo(self): return {"category": self.category, "id": self.eid, "name": self.eid.split("/")[-1]}
    def GetFusionComp(self): return self.comp


class FusionTitleItem(Item):
    def __init__(self, name, tools, start=0, dur=120):
        super().__init__(name, start, dur, "title")
        if isinstance(tools, str):
            self.comps = [("Composition 1", comp_from_lua(tools, self))]
        else:
            self.comps = [("Composition 1", FusionComp(tools, self))]
        self.active = 0

    @property
    def comp(self): return self.comps[self.active][1]
    def GetFusionCompCount(self): return len(self.comps)
    def GetFusionCompByIndex(self, i): return self.comps[i - 1][1] if 1 <= i <= len(self.comps) else None
    def GetFusionCompNameList(self): return [n for n, _ in self.comps]
    def GetFusionCompByName(self, n): return next((c for k, c in self.comps if k == n), None)

    def LoadFusionCompByName(self, n):
        for i, (k, _c) in enumerate(self.comps):
            if k == n:
                self.active = i
                return self.comps[i][1]
        return None

    def ImportFusionComp(self, path):
        self.calls.append(("ImportFusionComp", self.name, path))
        if not os.path.isfile(path):
            return None
        c = comp_from_lua(open(path, encoding="utf-8").read(), self)
        self.comps.append((f"Composition {len(self.comps) + 1}", c))
        return c

    def DeleteFusionCompByName(self, n):
        # measured on 21.1.1: a clip's LAST comp cannot be deleted
        self.calls.append(("DeleteFusionCompByName", self.name, n))
        if len(self.comps) < 2 or not any(k == n for k, _c in self.comps):
            return False
        cur = self.comps[self.active]
        self.comps = [(k, c) for k, c in self.comps if k != n]
        self.active = next((i for i, kc in enumerate(self.comps) if kc is cur), len(self.comps) - 1)
        return True

    def GetTrackTypeAndIndex(self):
        tl = getattr(self, "tl", None)
        for (kind, i), lst in (tl.items.items() if tl else []):
            if self in lst:
                return [kind, i]
        return []

    def SetPosition(self, pos, moveLinkedItems=True, subframePrecision=False):
        # [stub 21.1.2] — what the fake assumes until L1-a: it moves the item, refuses an overlap or a locked track,
        # and ripples nothing
        tl = getattr(self, "tl", None)
        self.calls.append(("SetPosition", self.name, dict(pos)))
        if tl is None:
            return False
        cur = self.GetTrackTypeAndIndex()
        ti, sf = int(pos.get("trackIndex", cur[1])), int(pos.get("startFrame", self.start))
        if ti > tl.tracks.get("video", 0) or getattr(tl, "locked", {}).get(("video", ti)):
            return False
        dst = tl.items.setdefault(("video", ti), [])
        if any(x is not self and x.start < sf + self.dur and sf < x.start + x.dur for x in dst):
            return False
        tl.items[tuple(cur)].remove(self)
        self.start = sf
        dst.append(self)
        return True


class FontList:
    def __init__(self, fonts): self.fonts = fonts
    def GetFontList(self): return {k: list(v) for k, v in self.fonts.items()}     # [stub: L1-e reads the real shape]

    def AddFont(self, path):
        if not os.path.isfile(path) or getattr(self, "needs_restart", False):
            return False
        sys.path.insert(0, HERE)
        import title_card as TC
        f = TC.read_font(path)
        self.fonts.setdefault(f["family"], []).append(f["subfamily"])
        return True


class Fusion:
    def __init__(self, templates, fonts=None, live=True):
        self.templates, self.fonts, self.live = templates, FontList(fonts if fonts is not None else {}), live
    def MapPath(self, path): return self.templates if path == "Templates:" else path
    def FontManager(self): return self.fonts

    def InstallFile(self, path, quiet=False):
        import zipfile
        if not os.path.isfile(path):
            return False
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".setting") and self.live:                # [stub: L1-f — live, or after a restart]
                    INSTALLED[n.split("/")[-1][: -len(".setting")]] = z.read(n).decode("utf-8")
        return True


class MediaPool:
    def __init__(self, calls, project): self.calls, self.project = calls, project

    def ImportMedia(self, paths):
        self.calls.append(("ImportMedia", list(paths)))
        out = []
        for x in paths:
            f = x if isinstance(x, str) else x.get("FilePath", "")
            if f.lower().endswith(".srt"):
                if getattr(self.project, "srt_import_fails", False):
                    continue
                out.append(MediaPoolItem(os.path.basename(f), srt=f))
            else:
                out.append(MediaPoolItem(os.path.basename(f)))
        return out

    def GetRootFolder(self): return Folder(getattr(self.project, "pool", []))

    def AppendToTimeline(self, infos):
        # recordFrame is absolute (the timeline's own start frame plus the offset), like Resolve's
        if any(isinstance(i, dict) and i.get("mediaType") == 3 for i in infos):
            raise RuntimeError("Resolve crashed (measured 21.1.1: mediaType 3 on an .srt)")
        self.calls.append(("AppendToTimeline", [{k: v for k, v in i.items() if k != "mediaPoolItem"} if isinstance(i, dict)
                                                else {"item": i.file_name} for i in infos]))
        tl, out = self.project.timeline, []
        for i in infos:
            if isinstance(i, MediaPoolItem):                # a bare item: at the playhead, on a subtitle track for an
                if i.srt:                                     # .srt (measured: the playhead at the start → frame 0)
                    if not tl.tracks.get("subtitle"):
                        tl.tracks["subtitle"] = 1
                    rec = getattr(tl, "playhead", tl.start)
                    lst = tl.items.setdefault(("subtitle", 1), [])
                    for t0, t1, text in _srt_cues(i.srt):
                        lst.append(Item(text, rec + round(t0 * tl.fps), round((t1 - t0) * tl.fps), kind="subtitle"))
                    out.append(Item(i.file_name, rec, 1, kind="subtitle"))
                continue
            mpi = i["mediaPoolItem"]
            ti, rec = int(i.get("trackIndex", 1)), int(i.get("recordFrame", tl.start))
            if mpi.title:
                n = int(i.get("endFrame", 119)) - int(i.get("startFrame", 0)) + 1
                lst = tl.items.setdefault(("video", ti), [])
                if any(x.start < rec + n and rec < x.start + x.dur for x in lst):
                    out.append(Item("dead handle", 0, 0))      # AutoSubs: a dead handle when the slot is taken
                    continue
                it = FusionTitleItem(mpi.title, FUSION_TITLES[mpi.title], start=rec, dur=n)
                lst.append(it)
                out.append(it)
                continue
            if mpi.srt:
                lst = tl.items.setdefault(("subtitle", ti), [])
                for t0, t1, text in _srt_cues(mpi.srt):
                    lst.append(Item(text, rec + round(t0 * tl.fps), round((t1 - t0) * tl.fps), kind="subtitle"))
                out.append(Item(mpi.file_name, rec, 1, kind="subtitle"))
                continue
            # a source range (startFrame..endFrame, the last frame in — as titles take it) sets the length; without one
            # the whole file (720 frames here). `audio_ranges_ignored`: a Resolve that drops the range, for the read-back
            n = (int(i["endFrame"]) - int(i.get("startFrame", 0)) + 1
                 if "endFrame" in i and not getattr(self.project, "audio_ranges_ignored", False) else 720)
            it = Item(i["mediaPoolItem"].file_name, int(i.get("recordFrame", tl.start)), n, kind="audio")
            tl.items.setdefault(("audio", int(i.get("trackIndex", 1))), []).append(it)
            out.append(it)
        return out

    def CreateEmptyTimeline(self, name):
        self.calls.append(("CreateEmptyTimeline", name))
        tl = Timeline(self.calls, name=name, length=0)
        tl.items = {}
        self.project.made.append(tl)
        return tl


class Timeline:
    def __init__(self, calls, name="T-cut", fps=24.0, start=86400, length=240, w=1080, h=1920):
        self.calls, self.name, self.fps, self.start, self.length = calls, name, fps, start, length
        self.w, self.h = w, h                     # HR-07: render-mp4.py reads the timeline's size back
        self.tracks = {"video": 1, "audio": 1}
        self.names, self.markers = {}, {}
        self.graph = Graph(calls, nodes=0)        # measured: no timeline grade → 0 nodes
        # measured on 21.1: a transition comes back from GetItemListInTrack as an item of its own
        self.items = {("video", 1): [Item("S1-C1_host_kling_v1.mp4", start, 120),
                                     Item("Cross Dissolve", start + 114, 12, "transition"),
                                     Item("S2_host_kling_v1.mp4", start + 120, 120)]}

    def GetName(self): return self.name
    def GetStartFrame(self): return self.start
    def GetEndFrame(self): return self.start + self.length

    def GetSetting(self, key):
        if key == "timelineFrameRate":
            return self.fps
        s = getattr(self, "settings", {})
        if key in s:
            return s[key]
        # Resolve returns settings as strings
        return {"timelineResolutionWidth": str(self.w), "timelineResolutionHeight": str(self.h)}.get(key)

    def SetSetting(self, key, value):
        self.calls.append(("SetSetting", self.name, key, value))
        self.settings = getattr(self, "settings", {})
        self.settings[key] = str(value)
        return True

    def SetCurrentTimecode(self, tc):
        self.calls.append(("SetCurrentTimecode", tc))
        h, m, s_, f = [int(x) for x in tc.split(":")]
        self.playhead = ((h * 60 + m) * 60 + s_) * round(self.fps) + f
        return True

    def SetMarkInOut(self, a, b, kind=None):
        self.calls.append(("SetMarkInOut", a, b))
        self.marks = (int(a), int(b))
        return True

    def ClearMarkInOut(self, kind=None):
        self.marks = None
        return True

    def SetTrackLock(self, kind, i, on):
        self.calls.append(("SetTrackLock", kind, i, on))
        self.locked = getattr(self, "locked", {})
        self.locked[(kind, i)] = bool(on)
        return True

    def GetIsTrackLocked(self, kind, i): return getattr(self, "locked", {}).get((kind, i), False)

    def InsertFusionTitleIntoTimeline(self, name):
        # measured on 21.1.1 (a supplement ad job): it lands on the TOPMOST UNLOCKED video track, at the playhead, for the
        # mark in–out (120 frames without marks); every other unlocked track ripples by that length; under a locked
        # track above it, it fails silently
        self.calls.append(("InsertFusionTitleIntoTimeline", self.name, name))
        if name not in FUSION_TITLES and name not in INSTALLED:
            return None
        lk = getattr(self, "locked", {})
        nv = self.tracks.get("video", 0)
        unlocked = [i for i in range(1, nv + 1) if not lk.get(("video", i))]
        if not unlocked or max(unlocked) != nv:
            return None
        top = max(unlocked)
        marks = getattr(self, "marks", None)
        start = marks[0] if marks else getattr(self, "playhead", self.start)
        dur = marks[1] - marks[0] + 1 if marks else 120
        for (kind, i), lst in self.items.items():
            if (kind, i) == ("video", top) or lk.get((kind, i)):
                continue
            for x in lst:
                if x.start >= start:
                    x.start += dur                           # the ripple
        it = FusionTitleItem(name, FUSION_TITLES[name] if name in FUSION_TITLES else INSTALLED[name], start=start, dur=dur)
        it.calls, it.tl = self.calls, self
        self.items.setdefault(("video", top), []).append(it)
        return it
    def GetTrackCount(self, kind): return self.tracks.get(kind, 0)

    def ExportFrame(self, offset, opts=None):
        # [stub 21.1.2] Timeline.ExportFrame: recorded with the title tracks' state at that moment (the review loop)
        self.calls.append(("ExportFrame", self.name, int(offset), (opts or {}).get("filePath")))
        if not getattr(self, "export_frame", True):
            raise AttributeError("ExportFrame")
        state = {i: self.GetIsTrackEnabled("video", i) for i in range(1, self.tracks.get("video", 0) + 1)}
        self.exported = getattr(self, "exported", []) + [(int(offset), (opts or {}).get("filePath"), state)]
        return {"success": True}

    def DeleteTrack(self, kind, i):
        self.calls.append(("DeleteTrack", kind, i))
        n = self.tracks.get(kind, 0)
        if not 1 <= i <= n:
            return False
        self.items.pop((kind, i), None)
        for j in range(i + 1, n + 1):
            for d in (self.items, self.names, getattr(self, "locked", {})):
                if (kind, j) in d:
                    d[(kind, j - 1)] = d.pop((kind, j))
        self.names.pop((kind, n), None)
        self.tracks[kind] = n - 1
        return True

    def DuplicateTimeline(self, name):
        self.calls.append(("DuplicateTimeline", self.name, name))
        tl = Timeline(self.calls, name=name, fps=self.fps, start=self.start, length=self.length, w=self.w, h=self.h)
        tl.tracks, tl.names = dict(self.tracks), dict(self.names)
        tl.items = {k: list(v) for k, v in self.items.items()}           # the same clips, its own track lists
        if getattr(self, "project", None):
            tl.project = self.project
            self.project.made.append(tl)
        return tl
    def GetTrackName(self, kind, i): return self.names.get((kind, i), f"{kind} {i}")
    def GetItemListInTrack(self, kind, i): return self.items.get((kind, i), [])
    def GetMarkers(self): return dict(self.markers)
    def GetNodeGraph(self): return self.graph

    def AddTrack(self, kind, *sub):
        self.calls.append(("AddTrack", kind) + tuple(sub))
        self.tracks[kind] = self.tracks.get(kind, 0) + 1
        self.subtypes = getattr(self, "subtypes", {})
        self.subtypes[(kind, self.tracks[kind])] = sub[0] if sub else "mono"
        return True

    def SetTrackEnable(self, kind, i, on):
        self.calls.append(("SetTrackEnable", kind, i, on))
        if kind == "subtitle":
            return True                    # measured 21.1.1: accepted, and the subtitle track stays on
        self.enabled = getattr(self, "enabled", {})
        self.enabled[(kind, i)] = bool(on)
        return True

    def GetIsTrackEnabled(self, kind, i): return getattr(self, "enabled", {}).get((kind, i), True)

    def SetTrackName(self, kind, i, name):
        self.calls.append(("SetTrackName", kind, i, name))
        self.names[(kind, i)] = name
        return True

    def AddMarker(self, frame, color, name, note, duration, custom=""):
        # measured: a frame past the timeline's end is accepted and returns True
        self.calls.append(("AddMarker", frame))
        if frame in self.markers:
            return False
        self.markers[frame] = {"color": color, "name": name, "note": note, "duration": duration, "customData": custom}
        return True


class Project:
    def __init__(self, calls, name="fx-01001-T", timeline=None, jobs=None, coerce=None):
        self.calls, self.name = calls, name
        self.timeline = timeline or Timeline(calls)
        self.jobs = [dict(j) for j in (jobs or [])]
        self.settings, self.coerce, self.resolve, self._n = {}, coerce or {}, None, 0
        self.made = []
        self.first = self.timeline
        self.timeline.project = self

    def GetName(self): return self.name
    def GetCurrentTimeline(self): return self.timeline
    def GetTimelineCount(self): return 1 + len(self.made)
    def GetTimelineByIndex(self, i): return ([getattr(self, "first", None) or self.timeline] + self.made)[i - 1]

    def ApplyFairlightPresetToCurrentTimeline(self, name):
        self.calls.append(("ApplyFairlightPresetToCurrentTimeline", name))
        return True
    def GetMediaPool(self): return MediaPool(self.calls, self)

    def ExportCurrentFrameAsStill(self, path):
        self.calls.append(("ExportCurrentFrameAsStill", path))
        self.stills = getattr(self, "stills", []) + [path]
        return True

    def SetCurrentTimeline(self, tl):
        self.calls.append(("SetCurrentTimeline", tl.GetName()))
        self.timeline = tl
        return True
    def GetSetting(self, key): return self.timeline.GetSetting(key)
    def GetRenderFormats(self): return {"MP4": "mp4", "QuickTime": "mov"}           # {name: id}
    def GetRenderCodecs(self, fmt): return {"H.264": "H264", "H.265": "H265"} if fmt == "mp4" else {}
    def GetRenderJobList(self): return [dict(j) for j in self.jobs]
    def RefreshLUTList(self): return True

    def GetColorGroupsList(self): return list(getattr(self, "groups", []))

    def AddColorGroup(self, name):
        self.calls.append(("AddColorGroup", name))
        self.groups = getattr(self, "groups", [])
        if any(g.GetName() == name for g in self.groups):
            return None
        g = ColorGroup(self.calls, name)
        self.groups.append(g)
        return g

    def SetCurrentRenderFormatAndCodec(self, fmt, codec):
        self.calls.append(("SetCurrentRenderFormatAndCodec", fmt, codec))
        return (fmt, codec) == ("mp4", "H264")

    def SetRenderSettings(self, d):
        self.calls.append(("SetRenderSettings", dict(d)))
        self.settings.update(d)
        if self.resolve:
            self.resolve.page = "deliver"          # measured: render calls switch to the Deliver page
        return True

    def AddRenderJob(self):
        self.calls.append(("AddRenderJob",))
        self._n += 1
        s = {**self.settings, **self.coerce}
        job = {"JobId": f"job-{self._n}", "TargetDir": s.get("TargetDir"),
               "OutputFilename": f"{s.get('CustomName')}.mp4", "TimelineName": self.timeline.name,
               "FormatWidth": s.get("FormatWidth"), "FormatHeight": s.get("FormatHeight"),
               "FrameRate": f"{s['FrameRate']:g}" if s.get("FrameRate") else "",   # measured: "24"
               "AudioSampleRate": s.get("AudioSampleRate"),
               "IsExportVideo": s.get("ExportVideo"), "IsExportAudio": s.get("ExportAudio")}
        self.jobs.append(job)
        return job["JobId"]

    def DeleteRenderJob(self, job_id):
        self.calls.append(("DeleteRenderJob", job_id))
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j["JobId"] != job_id]
        return len(self.jobs) < before


class ProjectManager:
    def __init__(self, calls, project):
        self.calls, self.project = calls, project

    def GetCurrentProject(self): return self.project

    def SaveProject(self):
        self.calls.append(("SaveProject",))
        return True


class Resolve:
    def __init__(self, calls, project):
        self.calls, self.pm, self.page = calls, ProjectManager(calls, project), "edit"
        project.resolve = self

    def GetProjectManager(self): return self.pm
    def GetFairlightPresets(self): return ["Cine Music", "Dialogue Bus"]
    def GetCurrentPage(self): return self.page
    def GetVersionString(self): return getattr(self, "version", "21.1.1")

    def Fusion(self):
        if getattr(self, "_fusion", None) is None:
            self._fusion = Fusion(getattr(self, "templates", ""), getattr(self, "fonts", None), getattr(self, "install_live", True))
        return self._fusion

    def GetEffectsList(self, media_type=None):
        # [read live 2026-10-29 on 21.1.2, abridged] {category, id, name}; titles and transitions are not listed
        if media_type == "audio":
            return [{"category": "audio", "id": "Fairlight FX/Dialogue Processor", "name": "Dialogue Processor"}]
        return [{"category": "fusion", "id": "Fusion/Effects/Krokodove/Bevel", "name": "Bevel"},
                {"category": "fusion", "id": "Fusion/Effects/Digital Glitch", "name": "Digital Glitch"},
                {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio/Continuous Zoom", "name": "Continuous Zoom"},
                {"category": "ofx", "id": "Open FX/MrAlexTech/MagicAnimate Free", "name": "MagicAnimate Free"},
                {"category": "ofx", "id": "Open FX/Higgsfield/Higgsfield Color Match", "name": "Higgsfield Color Match"}]

    def OpenPage(self, page):
        self.calls.append(("OpenPage", page))
        self.page = page
        return True


# ---------------------------------------------------------------------------------------------------
# the two environments
# ---------------------------------------------------------------------------------------------------
def sandbox_builtins() -> dict:
    """run_script's builtins: no open/exec/eval/compile, and the blocked imports raise."""
    b = dict(vars(builtins))
    for n in ("open", "exec", "eval", "compile", "input", "globals", "locals", "vars", "breakpoint"):
        b.pop(n, None)
    real = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".")[0] in SANDBOX_BLOCKED:
            raise PermissionError(f"import of '{name}' is blocked")
        return real(name, globals, locals, fromlist, level)
    b["__import__"] = guarded
    return b


def run(src: str, resolve: Resolve, mode: str) -> dict:
    g = {"__name__": "__resolve_script__", "resolve": resolve,
         "__builtins__": builtins if mode == "console" else sandbox_builtins()}
    if mode == "mcp":
        g["project"] = resolve.pm.project                 # run_script injects both
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, os.path.basename(RENDER if "render" in src[:200] else CONSOLE), "exec"), g)
    return g


def substitute(src: str, pairs) -> str:
    for old, new in pairs:
        if old not in src:
            raise AssertionError(f"the script no longer contains {old!r} — update this test with it")
        src = src.replace(old, new, 1)
    return src


def render_src(folder, name="T-v1-final", w=1080, h=1920, fps=24) -> str:
    return substitute(open(RENDER, encoding="utf-8").read(), [
        ('r"REPLACE-WITH-YOUR-PROJECT-FOLDER/10-export"', repr(folder)),
        ('"REPLACE-WITH-A-NAME"', repr(name)),
        ("\nWIDTH = None", f"\nWIDTH = {w}"),
        ("\nHEIGHT = None", f"\nHEIGHT = {h}"),
        ("\nFPS = None", f"\nFPS = {fps}"),
    ])


def console_src(markers=None, dump=False, dump_path=None) -> str:
    pairs = []
    if markers is not None:
        pairs.append(("MARKERS = []  # __DETECT_BEATS_MARKERS__",
                      f"MARKERS = {markers!r}  # __DETECT_BEATS_MARKERS__"))
    if dump:
        pairs.append(("\nDUMP_TIMELINE_JSON = False", "\nDUMP_TIMELINE_JSON = True"))
    if dump_path:
        pairs.append(('r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/timeline-dump.json"', repr(dump_path)))
    return substitute(open(CONSOLE, encoding="utf-8").read(), pairs)


def grade_src(plan: dict) -> str:
    sys.path.insert(0, HERE)
    import grade_luts as GL
    td = tempfile.mkdtemp(prefix="grade-copy-")
    os.makedirs(os.path.join(td, "07-edit"))
    return open(GL.console_copy(td, plan), encoding="utf-8").read()


def grade_plan(lane="drama") -> dict:
    sys.path.insert(0, HERE)
    import grade_luts as GL
    on = {"shot_match": True, "deflicker": False, "look": True, "texture": lane == "drama"}
    cdl = {"apply": True, "slope": [0.97, 1.0, 1.03], "offset": [0.01, 0.0, -0.01], "power": [1.0, 1.0, 1.0],
           "sat": 1.02, "de_before": 6.0, "de_after": 2.5}
    return {"job": "fx-01001-T", "lane": lane, "made": "2026-10-26T12:00", "node_map": GL.NODE_MAP,
            "template_drx": "/grades/clip-template.drx", "timeline_drx": "/grades/timeline-template.drx",
            "groups": {"MODEL kling3_0": {"model": "kling3_0", "pre_lut": "MCP/cine_kling3_0_norm_v1.cube"},
                       "MODEL seedance_2_5": {"model": "seedance_2_5", "pre_lut": "MCP/cine_seedance_2_5_norm_v1.cube"}},
            "clips": {"S1_kling_v1.mp4": {"shot": "S1", "group": "MODEL kling3_0", "profile": "talking_head",
                                          "look_lut": "MCP/cine_phone_60.cube", "nodes": dict(on), "cdl": cdl},
                      "S2_kling_v1.mp4": {"shot": "S2", "group": "MODEL kling3_0", "profile": "broll",
                                          "look_lut": "MCP/cine_phone_60.cube", "nodes": dict(on), "cdl": None},
                      "S3_seed_v1.mp4": {"shot": "S3", "group": "MODEL seedance_2_5", "profile": "broll",
                                         "look_lut": "MCP/cine_phone_60.cube", "nodes": dict(on), "cdl": None},
                      "S4_seed_v1.mp4": {"shot": "S4", "group": "MODEL seedance_2_5", "profile": "product",
                                         "look_lut": None, "nodes": {**on, "look": False, "texture": False},
                                         "cdl": None},
                      "S9_missing_v1.mp4": {"shot": "S9", "group": "MODEL kling3_0", "profile": "broll",
                                            "look_lut": None, "nodes": dict(on), "cdl": None}},
            "timeline": {"vignette": lane == "drama", "film_look": False}, "notes": []}


def grade_timeline(calls) -> Timeline:
    tl = Timeline(calls)
    tl.items = {("video", 1): [
        Item("S1_kling_v1.mp4", 86400, 48, graph=Graph(calls), calls=calls),                 # fresh: 1 empty node
        Item("Cross Dissolve", 86444, 8, "transition", calls=calls),
        Item("S2_kling_v1.mp4", 86448, 48, graph=Graph(calls, tools=[["Primary Balance"]]), calls=calls),
        Item("S3 renamed in the bin", 86496, 48, graph=Graph(calls, nodes=4), file_name="S3_seed_v1.mp4",
             calls=calls),                                                                    # 4 nodes, unlabelled
        Item("S4_seed_v1.mp4", 86544, 48, graph=Graph(calls, labels=["shot_match", "deflicker", "look", "texture"]),
             calls=calls),
        Item("someone_elses_title.mov", 86592, 48, graph=Graph(calls), calls=calls)]}
    return tl


def refused(src, resolve, mode, needle) -> tuple[bool, str]:
    try:
        run(src, resolve, mode)
    except RuntimeError as e:
        return needle in str(e), str(e)
    return False, "no refusal"


def std_timeline(calls) -> Timeline:
    """The plugin's own track layout (TRACK_LAYOUT): V1 Picture · V2 Graphics · V3 Titles · V4 Disclosure · V5 Supers."""
    tl = Timeline(calls)
    tl.tracks = {"video": 5, "audio": 2}
    tl.names = {("video", 1): "Picture", ("video", 2): "Graphics", ("video", 3): "Titles", ("video", 4): "Disclosure",
                ("video", 5): "Supers"}
    tl.items[("video", 2)] = [Item("L1-card.mp4", tl.start + 200, 40, calls=calls, path="/jobs/x/07-edit/gfx/L1-card.mp4")]
    tl.items[("video", 4)] = [Item("AI disclosure", tl.start, 240, "title", calls=calls)]
    return tl


def v245(td) -> None:
    """⚡ v2.45 (2026-10-29: "It keeps making mp4s which it imports"): the card's GENERATED Fusion titles
    (fusion_titles.py), placed by PLACE_TITLES on the plugin's own track layout, read back; options as Resolve stills;
    the installed library (resolve_library.py) through LIBRARY_SCAN, APPLY_TRANSITIONS and APPLY_EFFECTS."""
    print("resolve-production-console.py — v2.45: the card's generated Fusion titles on their named tracks (fusion_titles.py)")
    sys.path.insert(0, HERE)
    import native as NV
    import title_card as TC
    import fusion_titles as FT
    heavy = TC._sysfont("InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")
    regular = TC._sysfont("Inter-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf")
    if not (heavy and regular):
        print("  [skip] no system fonts to make a card that lints")
        return
    job = os.path.join(td, "sclp-native")
    T = os.path.join(job, "07-edit", "titles")
    os.makedirs(T)
    os.makedirs(os.path.join(job, "00-brief"))
    TC.propose(job, "ads", accent="#E8432E", page_bg="#111111")
    cp = os.path.join(job, TC.CARD)
    card = json.load(open(cp, encoding="utf-8"))
    fh, fr = TC.read_font(heavy), TC.read_font(regular)
    card["fonts"] = {"anchor": {"family": fh["family"], "file": heavy, "weight": int(fh["weight_class"])},
                     "companion": {"family": fr["family"], "file": regular, "weight": int(fr["weight_class"])}}
    card["kinds"]["super"] = {"kit": "super", "position": "lower", "max_count": 4}
    json.dump(card, open(cp, "w"), indent=1)
    specs_ = {"T1": {"kind": "hero", "at_s": 1.0, "duration_s": 2.5, "content": {"lines": ["Sleep through", "the night"],
                                                                                  "emphasis": "night"}},
              "P1": {"kind": "price", "at_s": 4.0, "duration_s": 1.5, "content": {"price": "$39", "was": "$59", "plate": True}},
              "T2": {"kind": "endcard", "at_s": 6.0, "duration_s": 3.0, "content": {"lines": ["Try it free"], "url": "x.com"}},
              "S1": {"kind": "super", "at_s": 3.5, "duration_s": 2.0, "content": {"lines": ["Clinically studied"], "plate": True}}}
    for tid, sp in specs_.items():
        json.dump(dict(sp, id=tid, anchor={"type": "cut", "at_s": sp["at_s"]}), open(os.path.join(T, f"{tid}.title.json"), "w"))
    csha = TC._sha(cp)
    want = {"T1": (3, 24, 60), "P1": (3, 96, 36), "T2": (3, 144, 72), "S1": (5, 84, 48)}

    def copy_(**kw):
        f, _nt, _nc, _sk, _no = NV.console_copy(job, **dict({"owner_paste": True}, **kw))   # the placing copy (rule 8)
        return open(f, encoding="utf-8").read()

    def fresh(version="21.1.2", fonts=None, live=True):
        calls = []
        tl = std_timeline(calls)
        p = Project(calls, timeline=tl)
        r = Resolve(calls, p)
        r.version, r.fonts, r.install_live = version, ({} if fonts is None else fonts), live
        return calls, tl, p, r

    def placed(tl):
        return {x.name[5:]: (k[1], x.start - tl.start, x.dur) for k, v in tl.items.items() if k[0] == "video"
                for x in v if str(x.name).startswith("cine:")}
    INSTALLED.clear()
    for mode in ("mcp", "console"):
        calls, tl, p, r = fresh()
        before = {k: [(x.name, x.start, x.dur) for x in v] for k, v in tl.items.items() if k in (("video", 1), ("video", 2), ("video", 4))}
        g = run(copy_(), r, mode)
        nat = (g.get("result") or {}).get("native") or {}
        ti = nat.get("titles") or {}
        rows = {x["id"]: x for x in ti.get("placed") or []}
        check(f"[{mode}] the plugin's own layout (Titles at V3 under Disclosure and Supers): hero, price and end card land on "
              f"V3 and the super on V5, at their frames for their lengths, named cine:<id> — PLACED",
              ti.get("verdict") == "PLACED" and placed(tl) == want, (ti.get("verdict"), placed(tl), ti.get("problems")))
        check(f"[{mode}] …through a scratch top track and 21.1.2's SetPosition: nothing rippled on Picture, Graphics or "
              f"Disclosure, the scratch track is gone, every lock put back",
              {k: [(x.name, x.start, x.dur) for x in v] for k, v in tl.items.items() if k in before} == before
              and tl.tracks["video"] == 5 and "_cine-insert" not in tl.names.values()
              and not any(getattr(tl, "locked", {}).values()) and all(rows[i].get("moved") for i in ("T1", "P1", "T2"))
              and "moved" not in rows["S1"], (rows.get("T1"), tl.names))
        it = {x.name[5:]: x for v in tl.items.values() for x in v if str(x.name).startswith("cine:")}
        comp = lambda i: it[i].comp                                                       # noqa: E731
        tool = lambda i, n: comp(i).FindTool(n)                                           # noqa: E731
        check(f"[{mode}] the import route (nothing installed): a stock Text+ with the generated comp imported and active; the "
              f"words on their tools — the price on TT_Main, the was on its own, the url on the end card's; a bool never",
              all(rows[i].get("route") == "import" and rows[i].get("template_missing") for i in want)
              and tool("T1", "TT_Main").inputs["StyledText"] == "Sleep through\nthe night"
              and tool("P1", "TT_Main").inputs["StyledText"] == "$39" and tool("P1", "was").inputs["StyledText"] == "$59"
              and tool("T2", "url").inputs["StyledText"] == "x.com"
              and tool("S1", "TT_Main").inputs["StyledText"] == "Clinically studied", rows.get("P1"))
        check(f"[{mode}] the read-back: the card's hash from the comp, the fold expression, the comp ends on the clip's last "
              f"frame, the face and its Style as set; written inside comp.Lock()",
              all(rows[i].get("card_sha256") == csha and "RenderEnd" in (rows[i].get("fold") or "")
                  and rows[i].get("render_end") == want[i][2] - 1 for i in want)
              and rows["T1"].get("font") == fh["family"] and rows["T1"].get("style") == TC.style_of(TC.load_card(cp))[1]
              and comp("T1").lock_calls > 0 and comp("T1").locks == 0, rows.get("T1"))
        check(f"[{mode}] the style: the plate kinds carry the card's plate on element 3 (price, super); the emphasised hero gets "
              f"the highlighter; the end card's page is opaque",
              tool("P1", "TT_Main").inputs["Enabled3"] == 1 and abs(tool("P1", "TT_Main").inputs["Alpha3"] - 0.72) < 1e-9
              and tool("S1", "TT_Main").inputs["Enabled3"] == 1 and tool("T1", "TT_Main").inputs["Enabled3"] == 1
              and tool("T1", "TT_Main").inputs["ElementShape3"] == 2 and tool("T2", "TT_Page").inputs["TopLeftAlpha"] == 1.0,
              tool("T1", "TT_Main").inputs)
        fonts = nat.get("fonts") or {}
        check(f"[{mode}] CHECK_FONTS: the face was missing from Resolve's list, AddFont took the card's files, and every row "
              f"reads the face as installed",
              fonts.get("added") and all(x.get("installed") for x in fonts.get("faces") or [])
              and all(rows[i].get("font_installed") is True for i in want), fonts)
        offs = [e[0] for e in getattr(tl, "exported", [])]
        check(f"[{mode}] a still of each title at its hold through Timeline.ExportFrame (no playhead move), and the row "
              f"records it", sorted(offs) == sorted(f + n // 2 for _t, f, n in want.values())
              and all(rows[i].get("still") for i in want), offs)
        n_ins = sum(1 for c in calls if c[0] in ("InsertFusionTitleIntoTimeline", "ImportFusionComp"))
        g = run(copy_(), r, mode)
        ti2 = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
        check(f"[{mode}] run again: every title found by its name cine:<id> at its frame, its words rewritten, nothing "
              f"inserted or imported again",
              ti2.get("verdict") == "PLACED" and all(x.get("already") for x in ti2.get("placed") or [])
              and sum(1 for c in calls if c[0] in ("InsertFusionTitleIntoTimeline", "ImportFusionComp")) == n_ins
              and placed(tl) == want, ti2.get("problems"))
        if mode == "mcp":
            gd = run(console_src([], dump=True), r, "mcp")
            dmp = (gd.get("result") or {}).get("timeline_dump") or {}
            v2 = (dmp.get("tracks") or {}).get("video2") or []
            check("[mcp] DUMP_TIMELINE_JSON carries each item's media file (export reads the timeline for title movies); a "
                  "title has none",
                  v2 and v2[0].get("file") == "/jobs/x/07-edit/gfx/L1-card.mp4"
                  and all(x.get("file") is None for x in (dmp.get("tracks") or {}).get("video3") or []), v2)
            json.dump(dmp, open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
            sy = NV.sync_specs(job)
            check("[mcp] native.py sync-specs matches each title by its name cine:<id> — nothing to rewrite, nothing new",
                  not sy["created"] and not sy["unplaced"] and not sy["words_changed"], sy)
            os.remove(os.path.join(job, "07-edit", "timeline-dump.json"))
    # a Resolve without SetPosition: the measured rule comes back, and nothing is left on a scratch track
    calls, tl, p, r = fresh(version="21.1.1")
    g = run(copy_(), r, "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("Resolve 21.1.1 (no TimelineItem.SetPosition): the titles under another track are NOT placed, the report says "
          "bottom-up and why; the super on the top track is; no scratch track was made",
          ti.get("verdict") == "NOT ALL PLACED" and set(placed(tl)) == {"S1"}
          and all("bottom-up" in (x.get("problem") or "") and "SetPosition" in x["problem"] for x in ti["placed"] if x["id"] != "S1")
          and tl.tracks["video"] == 5 and not any(c[0] == "AddTrack" for c in calls), ti.get("problems"))
    # route T: installed by fusion.InstallFile — then the template comes back by its name
    calls, tl, p, r = fresh()
    g = run(copy_(install=True), r, "mcp")
    nat = (g.get("result") or {}).get("native") or {}
    rows = {x["id"]: x for x in (nat.get("titles") or {}).get("placed") or []}
    check("INSTALL_TITLE_TEMPLATES: the .drfx installed, each title inserted by its own name (the template route), nothing "
          "imported",
          (nat.get("install") or {}).get("installed") and all(rows[i].get("route") == "template" for i in want)
          and not any(c[0] == "ImportFusionComp" for c in calls) and (nat.get("titles") or {}).get("verdict") == "PLACED",
          (nat.get("install"), {i: rows[i].get("route") for i in rows}))
    calls, tl, p, r = fresh(live=False)
    INSTALLED.clear()
    g = run(copy_(install=True), r, "mcp")
    rows = {x["id"]: x for x in (((g.get("result") or {}).get("native") or {}).get("titles") or {}).get("placed") or []}
    check("…an install that needs a restart (Resolve does not list the name yet): route auto imports the comp, and says so",
          all(rows[i].get("route") == "import" and "not installed" in (rows[i].get("template_missing") or "") for i in want), rows)
    # a stale template: the comp's hash is not the card's
    calls, tl, p, r = fresh()
    src = copy_().replace(f"'card_sha256': '{csha}'", "'card_sha256': '" + "0" * 64 + "'")
    g = run(src, r, "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("a template whose hash is not the card's is refused (\"does not carry this card's hash\"): NOT ALL PLACED, never "
          "used", ti.get("verdict") == "NOT ALL PLACED"
          and all("does not carry this card's hash" in (x.get("problem") or "") for x in ti.get("placed") or []), ti.get("problems"))
    run(copy_(install=True), r, "mcp")            # installs the current card's templates
    g = run(copy_(install=True).replace('TITLE_ROUTE = "auto"', 'TITLE_ROUTE = "template"', 1)
            .replace(f"'card_sha256': '{csha}'", "'card_sha256': '" + "1" * 64 + "'"), r, "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("…route template with a title on the timeline from another card: refused, naming both hashes",
          all("generated from another card" in (x.get("problem") or "") for x in ti.get("placed") or []), ti.get("problems"))
    # fonts: missing and not added → not placed
    calls, tl, p, r = fresh()
    g = run(copy_(add_fonts=False), r, "mcp")
    nat = (g.get("result") or {}).get("native") or {}
    check("the face missing from Resolve and no AddFont: every row reads font_installed false, NOT ALL PLACED, and the fonts "
          "report names the one manual step",
          (nat.get("titles") or {}).get("verdict") == "NOT ALL PLACED"
          and all(x.get("font_installed") is False for x in (nat.get("titles") or {}).get("placed") or [])
          and any("restart Resolve" in x for x in (nat.get("fonts") or {}).get("problems") or []), nat.get("fonts"))
    # the timeline at another rate than the template
    calls, tl, p, r = fresh()
    tl.fps = 25.0
    g = run(copy_(), r, "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("a template generated at 24 fps on a 25 fps timeline is refused (its keys are frames): build --fps 25",
          all("--fps 25" in (x.get("problem") or "") for x in ti.get("placed") or []), ti.get("problems"))

    print("resolve-production-console.py — v2.45: PLACE_TITLE_OPTIONS, the review loop as Resolve stills")
    for n_ in (1, 2, 3):
        json.dump({"id": f"T1.opt{n_}", "kind": "hero", "at_s": 1.0, "duration_s": 2.5, "anchor": {"type": "cut", "at_s": 1.0},
                   "content": {"lines": [["Sleep through", "the night"], ["Wake up", "rested"], ["Deep sleep", "tonight"]][n_ - 1]}},
                  open(os.path.join(T, f"T1.opt{n_}.title.json"), "w"))
    calls, tl, p, r = fresh()
    tl.names[("video", 1)] = "Picture"
    g0 = run(substitute(open(CONSOLE, encoding="utf-8").read(), [("\nSNAPSHOT_TIMELINE = False", "\nSNAPSHOT_TIMELINE = True"),
                                                                 ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
                                                                 ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")]), r, "mcp")
    snap_p = os.path.join(td, "snap-v245.json")
    json.dump(((g0.get("result") or {}).get("native") or {}).get("snapshot") or {}, open(snap_p, "w"))
    cut_items = {k: [(x.name, x.start) for x in v] for k, v in tl.items.items()}
    src = copy_(titles=False, options="T1", expect=snap_p)
    g = run(src, r, "mcp")
    nat = (g.get("result") or {}).get("native") or {}
    op = ((nat.get("options") or {}).get("titles") or {}).get("T1") or {}
    dup = next((t for t in p.made if t.name == "T-cut — OPTIONS T1"), None)
    check("the options on a duplicate \"<cut> — OPTIONS T1\", each on its own Titles opt<N> track at the spec's frame",
          dup is not None and op.get("verdict") == "STILLS"
          and sorted(dup.names.get(("video", r_["track_index"])) for r_ in op.get("rows") or []) == ["Titles opt1", "Titles opt2", "Titles opt3"]
          and all(r_.get("record_frame") == 24 for r_ in op.get("rows") or []), (op.get("rows"), getattr(dup, "names", None)))
    ex = getattr(dup, "exported", []) if dup else []
    textual = [i for i in range(1, (dup.tracks["video"] if dup else 0) + 1)
               if (dup.names.get(("video", i)) or "").lower().startswith(("titles", "supers", "disclosure", "captions"))] if dup else []
    on_ok = all([i for i in textual if st[i]] == [next(r_["track_index"] for r_ in op["rows"] if f"opt{r_['option']}_" in path)]
                for _o, path, st in ex if path.endswith("_on.png"))
    off_ok = all(not any(st[i] for i in textual) for _o, path, st in ex if path.endswith("_off.png"))
    check("Resolve's own stills: 5 moments × on and off per option (30), each 'on' with only its option's track enabled, each "
          "'off' with every title track off; the files where strip-native reads them",
          len(ex) == 30 and on_ok and off_ok and all(path.startswith(f"{job}/09-qa/titles/T1/opt") for _o, path, _s in ex)
          and sorted({path.rsplit("/", 1)[1].split("_")[1] for _o, path, _s in ex}) == sorted(["entrance", "legible", "mid", "exit", "gone"]),
          [(o_, path) for o_, path, _s in ex][:6])
    check("…the cut is untouched: the same items, the current timeline is the cut again, the invariant held; the duplicate's "
          "tracks are enabled as they were",
          {k: [(x.name, x.start) for x in v] for k, v in tl.items.items()} == cut_items and p.timeline is tl
          and nat.get("invariant") == [] and dup is not None and all(dup.GetIsTrackEnabled("video", i) for i in textual),
          nat.get("invariant"))
    n_dup = sum(1 for c in calls if c[0] == "DuplicateTimeline")
    run(src, r, "mcp")
    check("…run again: the duplicate is reused and nothing is placed twice",
          sum(1 for c in calls if c[0] == "DuplicateTimeline") == n_dup
          and len([x for v in dup.items.values() for x in v if str(x.name).startswith("cine:T1.opt")]) == 3)

    print("resolve-production-console.py — v2.45: the installed library (resolve_library.py)")
    import resolve_library as RL
    for mode in ("mcp", "console"):
        calls = []
        r = Resolve(calls, Project(calls))
        troot = os.path.join(td, f"Templates-{mode}")
        os.makedirs(os.path.join(troot, "Edit", "Titles"))
        open(os.path.join(troot, "Edit", "Titles", "Background Reveal Lower Third.setting"), "w").write(
            '{ Tools = ordered() { BRL = MacroOperator { Inputs = ordered() { Input1 = InstanceInput { SourceOp = "T1", '
            'Source = "StyledText", Name = "Name", }, }, Tools = ordered() { } } } }')
        r.templates = troot
        lib_p = os.path.join(td, f"lib-{mode}.raw.json")
        src = substitute(open(CONSOLE, encoding="utf-8").read(), [("\nLIBRARY_SCAN = False", "\nLIBRARY_SCAN = True"),
                                                                  ('r"REPLACE-WITH-A-FOLDER/resolve-library.raw.json"', repr(lib_p))])
        g = run(src, r, mode)
        lib = (g.get("result") or {}).get("library") or (json.load(open(lib_p)) if os.path.isfile(lib_p) else {})
        if mode == "mcp":
            check("[mcp] LIBRARY_SCAN: GetEffectsList's Fusion, OFX and audio effects with category and id; no filesystem in "
                  "run_script, so no titles — and it says where to run for them",
                  len(lib.get("effects", {}).get("video") or []) == 5 and lib.get("templates") is None
                  and any("run_script_unsafe" in n for n in lib.get("notes") or []), lib)
        else:
            tpl_ = [t for t in lib.get("templates") or [] if t["name"] == "Background Reveal Lower Third"]
            check("[console] LIBRARY_SCAN: and the template folders — a pack title with its published inputs",
                  tpl_ and tpl_[0]["published_inputs"] == [{"id": "Input1", "name": "Name", "source_op": "T1", "source": "StyledText"}],
                  tpl_)
            inv = RL.scan(os.path.join(td, "lib.json"), from_console=lib_p)
            check("…resolve_library.py scan --from-console maps it: the lower third, the Krokodove bevel as 3d-text, "
                  "MagicAnimate manual",
                  "Background Reveal Lower Third" in inv["kinds"].get("title/lower-third", [])
                  and "Bevel" in inv["kinds"].get("effect/3d-text", []) and any(m["name"] == "MagicAnimate Free" for m in inv["manual"]),
                  inv["kinds"])
    # the plan applied: transitions at their cuts, effects on named items
    jl = os.path.join(td, "lib-job")
    os.makedirs(os.path.join(jl, "07-edit"))
    os.makedirs(os.path.join(jl, "00-brief"))
    json.dump({"transitions": {"max_accents": 2}}, open(os.path.join(jl, "00-brief", "TITLE-CARD.json"), "w"))
    RL.scan(os.path.join(jl, RL.JOB_FILE), from_console=os.path.join(td, "lib-console.raw.json"),
            names=[_names_file(td)])
    json.dump({"transitions": [{"id": "J1", "at_s": 5.0, "kind": "zoom", "duration": 12},
                               {"id": "J2", "at_s": 10.0, "type": "Cross Dissolve", "duration": 12}],
               "effects": [{"id": "E1", "item": "B.mp4", "kind": "continuous-zoom", "inputs": {"Size": 1.08}},
                           {"id": "E2", "item": "C.mp4", "name": "MagicAnimate Free"}]}, open(os.path.join(jl, RL.PLAN_FILE), "w"))
    out_, TR, EF, N = RL.console_copy(jl, plan_p=os.path.join(jl, RL.PLAN_FILE))
    lsrc = open(out_, encoding="utf-8").read()

    def lib_tl(calls, no_handles=False):
        tl = Timeline(calls)
        tl.items = {("video", 1): [Item("A.mp4", tl.start, 120, calls=calls), Item("B.mp4", tl.start + 120, 120, calls=calls),
                                   Item("C.mp4", tl.start + 240, 96, calls=calls)]}
        for x in tl.items[("video", 1)]:
            x.tl = tl
        tl.no_handles = no_handles
        return tl
    calls = []
    tl = lib_tl(calls)
    p = Project(calls, timeline=tl)
    g = run(lsrc, Resolve(calls, p), "mcp")
    nat = (g.get("result") or {}).get("native") or {}
    trs = (nat.get("transitions") or {}).get("rows") or []
    efs = (nat.get("effects") or {}).get("rows") or []
    check("APPLY_TRANSITIONS: the zoom resolved to the pack's Smooth Zoom In (category fusion) and the dissolve to Cross "
          "Dissolve, each on the outgoing clip at its cut, both neighbours read back unchanged",
          [(x.get("type"), x.get("category"), x.get("placed"), x.get("neighbours_unchanged")) for x in trs]
          == [("Smooth Zoom In", "fusion", True, True), ("Cross Dissolve", "simple", True, True)]
          and len([x for x in tl.items[("video", 1)] if x.kind == "transition"]) == 2, trs)
    check("APPLY_EFFECTS: Continuous Zoom on B.mp4 through AddEffect(fusion, its id), its Size set through the effect's comp "
          "and read back; MagicAnimate on C.mp4 applied with its defaults and flagged MANUAL (In / Mid / Out)",
          efs[0].get("applied") and efs[0].get("inputs") == {"Size": True}
          and next(x for x in tl.items[("video", 1)] if x.name == "B.mp4").effects[0].comp.FindTool("Zoom").inputs["Size"] == 1.08
          and efs[1].get("applied") and "In / Mid / Out" in (efs[1].get("manual") or "")
          and (nat.get("effects") or {}).get("manual"), efs)
    n_add = sum(1 for c in calls if c[0] in ("AddEffect", "AddTransition"))
    run(lsrc, Resolve(calls, p), "mcp")
    check("…run again: the transitions are found at their cuts and the effects on their items — nothing added twice",
          sum(1 for c in calls if c[0] in ("AddEffect", "AddTransition")) == n_add)
    calls = []
    tl = lib_tl(calls, no_handles=True)
    g = run(lsrc, Resolve(calls, Project(calls, timeline=tl)), "mcp")
    trs = (((g.get("result") or {}).get("native") or {}).get("transitions") or {}).get("rows") or []
    check("a cut with no handle (the transition ate the incoming clip's frames): reported as a problem, never left silently",
          trs and all("ate frames" in (x.get("problem") or "") for x in trs), trs)

    print("the gate reads the v2.45 copies the way it is meant to")
    import gate as G
    # ⛔ v2.49 house rule 8: a copy that writes Fusion or places a title is DENIED through run_script (computer control)
    for name, s_ in (("the native placing copy (--owner-paste: generated titles, fonts, install)", copy_(install=True)),
                     ("the options copy (--owner-paste)", copy_(titles=False, options="T1")),
                     ("the library copy (a Fusion effect's inputs set by script)", lsrc)):
        d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": s_})
        check(f"{name} through run_script → deny, house rule 8 (Fusion and titles are computer control)",
              d["decision"] == "deny" and "computer-control rule" in d["reason"], d)
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": copy_(install=True, owner_paste=False)})
    check("the default native copy (v2.49: places no title) through run_script → not denied (setup, fonts check, reads)",
          d["decision"] != "deny", d)


def _names_file(td) -> str:
    p = os.path.join(td, "packs.txt")
    open(p, "w").write("# Transitions\nFree Smooth Transitions/Smooth Zoom In\n")
    lc = os.path.join(td, "lib-console.raw.json")
    json.dump({"library": {"resolve": "21.1.2", "effects": {"video": Resolve([], Project([])).GetEffectsList("video")}}},
              open(lc, "w"))
    return p


# ---------------------------------------------------------------------------------------------------
def main() -> int:
    td = tempfile.mkdtemp(prefix="console-scripts-")
    os.environ["CINE_HOME"] = os.path.join(td, "home")      # the gate must not see a real active job
    os.environ.pop("CINE_JOB", None)
    os.environ.pop("CINE_GATE", None)
    out = os.path.join(td, "10-export")

    print("render-mp4.py — against a fake Resolve, pasted into the console and through run_script")
    calls = []
    p = Project(calls)
    ok, why = refused(open(RENDER, encoding="utf-8").read(), Resolve(calls, p), "mcp", "CONFIG not edited")
    check("an unedited CONFIG refuses before touching Resolve", ok and not calls, (why, calls))

    for mode in ("console", "mcp"):
        calls = []
        p = Project(calls, jobs=[{"JobId": "hand-queued", "TargetDir": "/elsewhere", "OutputFilename": "b.mp4"},
                                 {"JobId": "stale", "TargetDir": out, "OutputFilename": "T-v1-final.mp4"}])
        r = Resolve(calls, p)
        g = run(render_src(out), r, mode)
        names = [c[0] for c in calls]
        res = g.get("result") or {}
        check(f"[{mode}] exactly one job queued and nothing started",
              names.count("AddRenderJob") == 1 and not any("Start" in n for n in names), names)
        check(f"[{mode}] the project is saved BEFORE the first render setting",
              "SaveProject" in names and names.index("SaveProject") < names.index("SetCurrentRenderFormatAndCodec"),
              names)
        check(f"[{mode}] a job queued by hand for another output survives",
              any(j["JobId"] == "hand-queued" for j in p.jobs), p.jobs)
        check(f"[{mode}] this output's earlier job is replaced, not duplicated",
              not any(j["JobId"] == "stale" for j in p.jobs) and res.get("replaced_jobs") == 1, res)
        check(f"[{mode}] format and codec are set by ID",
              ("SetCurrentRenderFormatAndCodec", "mp4", "H264") in calls, calls)
        check(f"[{mode}] the queued job reads back as CONFIG",
              bool(res.get("checks")) and all(res["checks"].values()), res)
        check(f"[{mode}] the page it switched to Deliver is put back", r.page == "edit", r.page)
    check("[console] the output folder is created; [mcp] it cannot be, and is not attempted",
          os.path.isdir(out))

    # ⛔ the sound-off proof (2026-10-27): T2, the picture alone, from a DUPLICATE — the editor's cut is never touched
    for mode in ("console", "mcp"):
        calls = []
        tl = Timeline(calls)
        tl.tracks = {"video": 3, "audio": 2, "subtitle": 1}
        tl.names = {("video", 2): "B-roll", ("video", 3): "Captions"}
        p = Project(calls, timeline=tl)
        src = render_src(out, name="T-v1-picture-only").replace("\nPICTURE_ONLY = False", "\nPICTURE_ONLY = True", 1)
        g = run(src, Resolve(calls, p), mode)
        res = g.get("result") or {}
        dup = next((t for t in p.made if t.name.endswith("PICTURE ONLY")), None)
        job_ = (res.get("job") or {})
        check(f"[{mode}] PICTURE_ONLY: one job, on the duplicate, with no audio",
              dup is not None and job_.get("TimelineName") == dup.name and job_.get("IsExportAudio") is False
              and all(res.get("checks", {}).values()), (res, [t.name for t in p.made]))
        st_ = next((c[1] for c in calls if c[0] == "SetRenderSettings"), {})
        check(f"[{mode}] PICTURE_ONLY: the Captions video track off on the duplicate only, and the subtitles left out of "
              f"the render (a subtitle track cannot be disabled by script — measured 21.1.1)",
              dup is not None and dup.enabled.get(("video", 3)) is False and ("video", 2) not in dup.enabled
              and not getattr(tl, "enabled", {}) and st_.get("ExportSubtitle") is False, (getattr(dup, "enabled", None), st_))
        check(f"[{mode}] PICTURE_ONLY: the editor is put back on the cut", p.timeline is tl, p.timeline.name)

    # ⛔ titles made in Resolve (house rule C7, 2026-10-27): the titles-off half of title_qa.py native, from a duplicate
    for mode in ("console", "mcp"):
        calls = []
        tl = Timeline(calls)
        tl.tracks = {"video": 3, "audio": 2, "subtitle": 1}
        tl.names = {("video", 2): "B-roll", ("video", 3): "Titles"}
        p = Project(calls, timeline=tl)
        src = render_src(out, name="T-v1-titles-off").replace("\nTITLES_OFF = False", "\nTITLES_OFF = True", 1)
        g = run(src, Resolve(calls, p), mode)
        res = g.get("result") or {}
        dup = next((t for t in p.made if t.name.endswith("TITLES OFF")), None)
        check(f"[{mode}] TITLES_OFF: one job, on a duplicate, the Titles track off there only, no audio, the subtitles as they were",
              dup is not None and (res.get("job") or {}).get("TimelineName") == dup.name and dup.enabled.get(("video", 3)) is False
              and ("video", 2) not in dup.enabled and ("subtitle", 1) not in dup.enabled and not getattr(tl, "enabled", {})
              and (res.get("job") or {}).get("IsExportAudio") is False and all(res.get("checks", {}).values()), (res, getattr(dup, "enabled", None)))
        check(f"[{mode}] TITLES_OFF: the editor is put back on the cut", p.timeline is tl, p.timeline.name)
    # ⚡ gate.py pre-lock (a supplement ad job, 2026-10-28): the three renders as filled copies — each runs as written, one job each
    sys.path.insert(0, HERE)
    import gate as _gate
    base_src = open(RENDER, encoding="utf-8").read()
    for key, folder, suffix, toggles, _why in _gate.PRELOCK_RENDERS:
        calls = []
        tl = Timeline(calls)
        tl.tracks = {"video": 3, "audio": 2, "subtitle": 1}
        tl.names = {("video", 2): "Graphics", ("video", 3): "Titles"}
        p = Project(calls, timeline=tl)
        src = _gate._fill_config(base_src, {"OUTPUT_FOLDER": os.path.join(td, "job", folder),
                                            "OUTPUT_FILENAME": f"T-v3-{suffix}", "TIMELINE_NAME": None,
                                            "WIDTH": 1080, "HEIGHT": 1920, "FPS": 24, **toggles})
        g = run(src, Resolve(calls, p), "mcp")
        res = g.get("result") or {}
        check(f"pre-lock {key}: the filled copy queues one job, named for its render, and starts nothing",
              [c[0] for c in calls].count("AddRenderJob") == 1 and not any("Start" in c[0] for c in calls)
              and all(res.get("checks", {}).values()), res)
    try:
        _gate._fill_config(base_src, {"NO_SUCH_SETTING": 1})
        check("pre-lock: a setting render-mp4.py does not have fails loudly", False)
    except ValueError:
        check("pre-lock: a setting render-mp4.py does not have fails loudly", True)
    calls = []
    tl = Timeline(calls)
    p = Project(calls, timeline=tl)
    ok, why = refused(render_src(out).replace("\nTITLES_OFF = False", "\nTITLES_OFF = True", 1), Resolve(calls, p), "mcp",
                      "No video track named like")
    check("TITLES_OFF with no titles track is refused, nothing queued, the cut current again",
          ok and "AddRenderJob" not in [c[0] for c in calls] and p.timeline is tl, (why, [c[0] for c in calls]))
    calls = []
    p = Project(calls)
    run(render_src(out).replace("\nBURN_SUBTITLES = None", "\nBURN_SUBTITLES = True", 1), Resolve(calls, p), "mcp")
    st = next((c[1] for c in calls if c[0] == "SetRenderSettings"), {})
    check("BURN_SUBTITLES = True asks Resolve to burn the Subtitle track in (ExportSubtitle + SubtitleFormat BurnIn)",
          st.get("ExportSubtitle") is True and st.get("SubtitleFormat") == "BurnIn", st)
    calls = []
    p = Project(calls)
    run(render_src(out), Resolve(calls, p), "mcp")
    st = next((c[1] for c in calls if c[0] == "SetRenderSettings"), {})
    check("BURN_SUBTITLES = None leaves the Deliver page's subtitle setting alone", "ExportSubtitle" not in st, st)
    calls = []
    ok, why = refused(render_src(out).replace("\nTITLES_OFF = False", "\nTITLES_OFF = True", 1)
                      .replace("\nPICTURE_ONLY = False", "\nPICTURE_ONLY = True", 1), Resolve(calls, Project(calls)), "mcp",
                      "two different renders")
    check("PICTURE_ONLY and TITLES_OFF together are refused", ok, why)

    calls = []
    p = Project(calls, name="Untitled Project 2026-09-14_144936")
    ok, why = refused(render_src(out), Resolve(calls, p), "mcp", "Untitled Project")
    check("an auto-named Untitled Project is refused before any render setting",
          ok and "SetRenderSettings" not in [c[0] for c in calls], (why, calls))

    calls = []
    p = Project(calls, timeline=Timeline(calls, fps=25.0))
    ok, why = refused(render_src(out, fps=24), Resolve(calls, p), "mcp", "fps")
    check("a timeline at 25 fps with CONFIG FPS 24 is refused, not retimed",
          ok and "SetRenderSettings" not in [c[0] for c in calls], (why, calls))

    # HR-07: the timeline's size against the delivery's WIDTH x HEIGHT, the same check as the fps
    calls = []
    p = Project(calls, timeline=Timeline(calls, w=1920, h=1012))
    ok, why = refused(render_src(out, w=1920, h=1080), Resolve(calls, p), "mcp", "1920x1012")
    check("HR-07: a 1920x1012 timeline with CONFIG 1920x1080 is refused before any render setting",
          ok and "SaveProject" not in [c[0] for c in calls] and "SetRenderSettings" not in [c[0] for c in calls],
          (why, calls))
    calls = []
    p = Project(calls, timeline=Timeline(calls, w=1080, h=1920))
    ok, why = refused(render_src(out, w=1920, h=1080), Resolve(calls, p), "mcp", "1080x1920")
    check("HR-07: a vertical timeline with a landscape CONFIG is refused", ok, why)
    calls = []
    p = Project(calls, timeline=Timeline(calls, w=1920, h=1080))
    res = (run(render_src(out, name="T-v1-landscape", w=1920, h=1080), Resolve(calls, p), "mcp").get("result") or {})
    check("HR-07: a 1920x1080 timeline with CONFIG 1920x1080 queues its job",
          [c[0] for c in calls].count("AddRenderJob") == 1 and all(res.get("checks", {}).values()), res)
    calls = []
    p = Project(calls, timeline=Timeline(calls, w=3840, h=2160))
    res = (run(render_src(out, name="T-v1-landscape", w=1920, h=1080), Resolve(calls, p), "mcp").get("result") or {})
    check("HR-07: a 3840x2160 timeline with CONFIG 1920x1080 (same shape, a scale at render) queues its job",
          [c[0] for c in calls].count("AddRenderJob") == 1, res)

    calls = []
    p = Project(calls, coerce={"AudioSampleRate": 44100})
    ok, why = refused(render_src(out), Resolve(calls, p), "mcp", "did not read back")
    check("a job that reads back wrong is removed again and the script refuses", ok and not p.jobs, (why, p.jobs))

    print("resolve-production-console.py — PLACE_TITLES and PLACE_SUBTITLES, from native.py console (house rule C7)")
    sys.path.insert(0, HERE)
    import native as NV
    import title_card as TC
    job = os.path.join(td, "fx-native")
    for d in ("00-brief", os.path.join("07-edit", "titles"), "08-captions"):
        os.makedirs(os.path.join(job, d), exist_ok=True)
    TC.propose(job, "ads", accent="#E8432E", page_bg="#111111")
    json.dump({"id": "T1", "kind": "hero", "duration_s": 2.5, "at_s": 1.0, "anchor": {"type": "settle", "at_s": 1.0},
               "content": {"lines": ["Sleep through", "the night"]}}, open(os.path.join(job, "07-edit", "titles", "T1.title.json"), "w"))
    json.dump({"id": "T2", "kind": "endcard", "duration_s": 3.0, "at_s": 6.0, "anchor": {"type": "cut", "at_s": 6.0},
               "content": {"lines": ["Try it free"]}}, open(os.path.join(job, "07-edit", "titles", "T2.title.json"), "w"))
    srtp = os.path.join(job, "08-captions", "fx.srt")
    open(srtp, "w").write("1\n00:00:00,500 --> 00:00:02,000\nEvery loaf\n\n2\n00:00:02,500 --> 00:00:04,000\nbefore six\n")

    def native_src(captions_as="track", template=None):
        f, _nt, _nc, _sk, _notes = NV.console_copy(job, srtp, captions_as, owner_paste=True)   # the placing copy (rule 8)
        src_ = open(f, encoding="utf-8").read()
        if template:
            src_ = src_.replace('TITLE_TEMPLATE = "Text+"', f"TITLE_TEMPLATE = {template!r}", 1)
        return src_
    json.dump(dict(json.load(open(os.path.join(job, "07-edit", "titles", "T1.title.json"))),
                   content={"lines": ["Sleep through", "the night"], "emphasis": "night"}),
              open(os.path.join(job, "07-edit", "titles", "T1.title.json"), "w"))
    for mode in ("mcp", "console"):
        calls = []
        p = Project(calls)
        tl = p.timeline
        v1_before = [(x.name, x.start) for x in tl.items[("video", 1)]]
        g = run(native_src(), Resolve(calls, p), mode)
        nat = (g.get("result") or {}).get("native") or {}
        ti = nat.get("titles") or {}
        rows = {r["id"]: r for r in ti.get("placed") or []}
        items = tl.GetItemListInTrack("video", ti.get("track_index") or 0)
        check(f"[{mode}] PLACE_TITLES: both titles on a new top 'Titles' track, at their frames for their lengths (the marks), "
              f"the words read back",
              ti.get("verdict") == "PLACED" and tl.names.get(("video", 2)) == "Titles" and len(items) == 2
              and [(x.start - tl.start, x.dur) for x in items] == [(24, 60), (144, 72)]
              and items[0].comp.tools[1].inputs["StyledText"] == "Sleep through\nthe night"
              and all(r.get("reads_back") for r in rows.values()), (ti, [(x.start, x.dur) for x in items]))
        check(f"[{mode}] …every other track locked for the insert, so the cut did not ripple, and the locks put back",
              [(x.name, x.start) for x in tl.items[("video", 1)]] == v1_before and not any(getattr(tl, "locked", {}).values())
              and ti.get("locks_restored", 0) >= 2, (v1_before, [(x.name, x.start) for x in tl.items[("video", 1)]],
                                                     getattr(tl, "locked", {})))
        t0 = items[0].comp.tools[1].inputs
        check(f"[{mode}] …the style frame applied and read back: H1, left at the margin, the highlighter on the emphasised title",
              t0["Size"] == 0.125 and t0["HorizontalLeftCenterRight"] == -1 and t0["Center"] == {1: 0.115, 2: 0.74}
              and t0["ElementShape3"] == 2 and t0["Offset3"] == {1: 0, 2: 0} and items[1].comp.tools[1].inputs["Level3"] == 0
              and not any(r.get("layout_misses") for r in rows.values()), (t0, rows))
        check(f"[{mode}] …a still of each title at its hold — Resolve's own frame (21.1.2 Timeline.ExportFrame, no playhead "
              f"move), not a screenshot",
              [e[0] for e in getattr(tl, "exported", [])] == [24 + 60 // 2, 144 + 72 // 2] and not getattr(p, "stills", [])
              and all(r.get("still") for r in rows.values()), getattr(tl, "exported", None))
        if mode == "mcp":
            # ⚡ a supplement ad job: once titles live in Resolve, their specs are rewritten from the timeline (native.py sync-specs)
            gd = run(console_src([], dump=True), Resolve(calls, p), "mcp")
            dmp = (gd.get("result") or {}).get("timeline_dump") or {}
            k_t = next((k for k, v in (dmp.get("track_names") or {}).items() if v == "Titles"), None)
            rows_t = (dmp.get("tracks") or {}).get(k_t or "", [])
            check("[mcp] DUMP_TIMELINE_JSON carries the track names and each title's words (for native.py sync-specs)",
                  bool(k_t) and [r.get("text") for r in rows_t] == ["Sleep through\nthe night", "Try it free"], dmp)
            if len(rows_t) == 2:
                t2p = os.path.join(job, "07-edit", "titles", "T2.title.json")
                t2_before = open(t2p, encoding="utf-8").read()
                rows_t[1].update(start=rows_t[1]["start"] + 12, start_s=round(rows_t[1]["start_s"] + 0.5, 3), text="Try it today")
                rows_t.append({"name": "Text+", "type": "video", "start": 200, "duration": 48, "start_s": 8.333,
                               "duration_s": 2.0, "text": "Free returns"})
                dpath = os.path.join(job, "07-edit", "timeline-dump.json")
                json.dump(dmp, open(dpath, "w"))
                dry = NV.sync_specs(job)
                check("native.py sync-specs (dry): T2 moved and re-worded, one title with no spec, T1 unchanged, nothing written",
                      [x.split(":")[0] for x in dry["updated"]] == ["T2"] and len(dry["created"]) == 1 and dry["words_changed"]
                      and any("re-anchor" in x for x in dry["problems"]) and json.load(open(t2p))["at_s"] == 6.0, dry)
                NV.sync_specs(job, write=True)
                t2 = json.load(open(t2p))
                new_ = [f for f in os.listdir(os.path.join(job, "07-edit", "titles")) if re.match(r"N\d+\.title\.json$", f)]
                check("native.py sync-specs --write: T2's time and words from the timeline, stamped with the dump; the new "
                      "title gets a spec",
                      t2["at_s"] == 6.5 and t2["content"]["lines"] == ["Try it today"]
                      and (t2.get("synced_from_timeline") or {}).get("dump_sha256") and len(new_) == 1, (t2, new_))
                open(t2p, "w", encoding="utf-8").write(t2_before)
                for f in new_ + ["../timeline-dump.json"]:
                    os.remove(os.path.normpath(os.path.join(job, "07-edit", "titles", f)))
        sp = nat.get("subtitles") or {}
        sub = tl.GetItemListInTrack("subtitle", sp.get("track") or 0)
        check(f"[{mode}] PLACE_SUBTITLES: the .srt appended with the playhead at the start (no mediaType), every cue read back",
              sp.get("verdict") == "PLACED" and len(sub) == 2 and [x.start - tl.start for x in sub] == [12, 60]
              and sp.get("pool_type") == "Subtitle", (sp, [(x.start, x.dur) for x in sub]))
        if mode == "console":
            check("[console] the placement report is written where title_card.py reads it",
                  os.path.isfile(os.path.join(job, "07-edit", "titles", "native-placement.json")))
        n_ins = sum(1 for c in calls if c[0] in ("InsertFusionTitleIntoTimeline", "AppendToTimeline"))
        g = run(native_src(), Resolve(calls, p), mode)
        nat = (g.get("result") or {}).get("native") or {}
        check(f"[{mode}] a second run adds nothing: the titles are found at their frames, the subtitles on their track",
              sum(1 for c in calls if c[0] in ("InsertFusionTitleIntoTimeline", "AppendToTimeline")) == n_ins
              and len(tl.GetItemListInTrack("video", 2)) == 2
              and (nat.get("subtitles") or {}).get("already") and (nat.get("titles") or {}).get("verdict") == "PLACED", nat)
    calls = []
    p = Project(calls)
    p.timeline.tracks = {"video": 3, "audio": 1}
    p.timeline.names = {("video", 1): "Picture", ("video", 2): "Titles", ("video", 3): "Supers"}
    g = run(native_src(), Resolve(calls, p), "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("a Titles track under another track: the insert cannot land there (measured), so nothing is placed and the "
          "report says to build the text tracks bottom-up",
          ti.get("verdict") == "NOT ALL PLACED" and any("bottom-up" in x for x in ti.get("problems") or [])
          and not p.timeline.GetItemListInTrack("video", 2), ti)
    calls = []
    p = Project(calls)
    g = run(native_src(template="Cinematic Title 07"), Resolve(calls, p), "mcp")
    ti = ((g.get("result") or {}).get("native") or {}).get("titles") or {}
    check("a template whose text hides behind a macro is reported: set the words by hand",
          ti.get("verdict") == "NOT ALL PLACED" and all("no Text+ tool" in (r.get("problem") or "") for r in ti.get("placed") or []), ti)
    calls = []
    p = Project(calls)
    g = run(native_src("textplus"), Resolve(calls, p), "mcp")
    cp = ((g.get("result") or {}).get("native") or {}).get("captions") or {}
    caps = p.timeline.GetItemListInTrack("video", cp.get("track_index") or 0)
    check("SUBTITLES_AS textplus: each cue a Text+ title on the 'Captions' track above the titles, its words read back",
          cp.get("verdict") == "PLACED" and len(caps) == 2 and caps[1].comp.tools[1].inputs["StyledText"] == "before six"
          and p.timeline.names.get(("video", cp.get("track_index"))) == "Captions", cp)
    calls = []
    p = Project(calls)
    p.srt_import_fails = True
    g = run(native_src(), Resolve(calls, p), "mcp")
    sp = ((g.get("result") or {}).get("native") or {}).get("subtitles") or {}
    check("an .srt the import does not take is NOT PLACED, with the one manual step",
          sp.get("verdict") == "NOT PLACED" and any("File ▸ Import ▸ Subtitle" in x for x in sp.get("problems") or []), sp)
    # the invariant check: a snapshot before, the copy with EXPECT_SNAPSHOT after
    calls = []
    p = Project(calls)
    p.timeline.names[("video", 1)] = "Picture"
    g = run(substitute(open(CONSOLE, encoding="utf-8").read(), [("\nSNAPSHOT_TIMELINE = False", "\nSNAPSHOT_TIMELINE = True"),
                                                                 ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
                                                                 ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")]),
            Resolve(calls, p), "mcp")
    snap = ((g.get("result") or {}).get("native") or {}).get("snapshot") or {}
    snap_p = os.path.join(td, "snap.json")
    json.dump(snap, open(snap_p, "w"))
    check("SNAPSHOT_TIMELINE reads every track's name, state and items (read-only)",
          snap.get("tracks", {}).get("video1", {}).get("name") == "Picture" and len(snap["tracks"]["video1"]["items"]) == 3
          and not [c for c in calls if c[0] in ("AddTrack", "SetTrackName", "InsertFusionTitleIntoTimeline")], snap)
    p.timeline.items[("video", 1)] = p.timeline.items[("video", 1)][:1]
    f, *_ = NV.console_copy(job, None, "track", False, None, snap_p)
    g = run(substitute(open(f, encoding="utf-8").read(), [("\nPLACE_TITLES = True", "\nPLACE_TITLES = False")])
            if "\nPLACE_TITLES = True" in open(f, encoding="utf-8").read() else open(f, encoding="utf-8").read(), Resolve(calls, p), "mcp")
    inv = ((g.get("result") or {}).get("native") or {}).get("invariant")
    check("…an edit that lost two clips from Picture is caught by name (the supers that vanished on a supplement ad job)",
          inv and "Picture" in inv[0] and "lost 2" in inv[0], inv)

    v245(td)

    print("resolve-production-console.py — against the same fake")
    beats = [(0, "Red", "Downbeat"), (24, "Blue", "Beat"), (480, "Blue", "Beat")]
    calls = []
    p = Project(calls)
    g = run(console_src(beats, dump=True), Resolve(calls, p), "mcp")
    res = g.get("result") or {}
    placed = [c[1] for c in calls if c[0] == "AddMarker"]
    check("[mcp] markers go in at the frames given — never shifted by the timeline start",
          placed == [0, 24, 480], placed)
    check("[mcp] every marker is read back, including the one past the current end",
          any("3/3 read back" in d and "1 past end" in d for d in res.get("done", [])), res)
    check("[mcp] V2 and the six named audio lanes exist",
          p.timeline.tracks == {"video": 2, "audio": 6}
          and p.timeline.GetTrackName("audio", 3) == "A3 ambience", (p.timeline.tracks, p.timeline.names))
    dump = res.get("timeline_dump") or {}
    items = dump.get("tracks", {}).get("video1", [])
    check("[mcp] the timeline dump comes back in result — frames relative to the start, seconds at the "
          "timeline's own rate, and a dissolve labelled a transition rather than counted as a shot",
          [(i["type"], i["start"], i["start_s"]) for i in items]
          == [("video", 0, 0.0), ("transition", 114, 4.75), ("video", 120, 5.0)], dump)

    dump_path = os.path.join(td, "timeline-dump.json")
    calls = []
    run(console_src([], dump=True, dump_path=dump_path), Resolve(calls, Project(calls)), "console")
    written = json.load(open(dump_path, encoding="utf-8")) if os.path.isfile(dump_path) else {}
    check("[console] the dump is written to DUMP_PATH", len(written.get("tracks", {}).get("video1", [])) == 3,
          written)

    raw = open(CONSOLE, encoding="utf-8").read()
    check("detect_beats.py's splice points are still in the template",
          "MARKERS = []  # __DETECT_BEATS_MARKERS__" in raw
          and '"""\nDaVinci Resolve — the ONE production/editing-setup console script' in raw)

    print("resolve-production-console.py — PLACE_MUSIC_FIT (music_fit.py rebuild: the ORIGINAL, by its segments)")
    # author, 2026-11-05: a Python render is a preview; A5 gets the original, cut by source range at whole frames
    segs = [{"src_in_f": 24, "src_out_f": 119, "record_f": 12}, {"src_in_f": 215, "src_out_f": 396, "record_f": 107}]
    mf = {"file": "/jobs/fx-01001-T/06-music/bed.wav", "sha256": "0" * 64, "track": 5, "record_offset_frames": 0,
          "segments": segs}
    music = [(6, "Red", "Phrase"), (240, "Green", "Hit H3 downbeat"), (145, "Yellow", "Nudge H2 -1f"),
             (107, "Cyan", "Music seam 1 — crossfade 3 ms", "add it in Fairlight by computer control", 1, ""),
             (270, "Cyan", "Music end — fade 750 ms", "to 12 s", 18, "")]
    for mode in ("mcp", "console"):
        calls = []
        p = Project(calls)
        src = substitute(console_src(music), [("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
                                               ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {mf!r}  # __MUSIC_FIT__")])
        g = run(src, Resolve(calls, p), mode)
        a5 = sorted(p.timeline.GetItemListInTrack("audio", 5), key=lambda it: it.GetStart())
        app = [c for c in calls if c[0] == "AppendToTimeline"]
        done = (g.get("result") or {}).get("done", [])
        check(f"[{mode}] the original is imported ONCE and each segment appended to A5 as a source range at its record "
              f"frame (recordFrame absolute, endFrame the last frame in), audio only",
              sum(1 for c in calls if c[0] == "ImportMedia") == 1 and len(app) == 1
              and app[0][1] == [{"startFrame": 24, "endFrame": 118, "mediaType": 2, "trackIndex": 5,
                                 "recordFrame": p.timeline.start + 12},
                                {"startFrame": 215, "endFrame": 395, "mediaType": 2, "trackIndex": 5,
                                 "recordFrame": p.timeline.start + 107}], app)
        check(f"[{mode}] both segments are read back at their frames and lengths, abutting — no mismatch reported",
              [(it.GetName(), it.GetStart() - p.timeline.start, it.GetDuration()) for it in a5]
              == [("bed.wav", 12, 95), ("bed.wav", 107, 181)]
              and any("2 segment(s) of the original on A5, read back 2/2" in d and "mismatch" not in d for d in done),
              (done, [(it.GetStart(), it.GetDuration()) for it in a5]))
        check(f"[{mode}] nothing in the music block touches Fairlight: no fade, crossfade or speed call",
              not [c for c in calls if any(k in str(c[0]) for k in ("Fade", "Crossfade", "Speed", "Retime", "Fairlight"))],
              calls)
        check(f"[{mode}] its markers go in with it: phrase, hit, nudge, the seam and the end fade, nothing per beat",
              sorted(p.timeline.markers) == [6, 107, 145, 240, 270] and p.timeline.markers[270]["duration"] == 18,
              p.timeline.markers)
        n_imp = sum(1 for c in calls if c[0] == "ImportMedia")
        g = run(src, Resolve(calls, p), mode)
        check(f"[{mode}] run again: the original already on A5 is left alone, nothing imported twice",
              sum(1 for c in calls if c[0] == "ImportMedia") == n_imp and len(p.timeline.GetItemListInTrack("audio", 5)) == 2,
              calls)
    calls = []
    p = Project(calls)
    p.audio_ranges_ignored = True                  # a Resolve that drops the range: the whole file lands twice
    g = run(substitute(console_src([]), [("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
                                         ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {mf!r}  # __MUSIC_FIT__")]),
            Resolve(calls, p), "mcp")
    done = (g.get("result") or {}).get("done", [])
    check("a segment whose length does not read back is reported, never silently left (and nothing deleted)",
          any("read back 0/2" in d and "segment 1: 720 frames at frame 12, planned 95" in d for d in done)
          and not [c for c in calls if "Delete" in str(c[0])], done)
    calls = []
    p = Project(calls)
    whole = dict(mf, segments=[])                  # a speed change: placed whole, the retime and cuts are Fairlight work
    g = run(substitute(console_src([]), [("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
                                         ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {whole!r}  # __MUSIC_FIT__")]),
            Resolve(calls, p), "mcp")
    a5 = p.timeline.GetItemListInTrack("audio", 5)
    app = [c for c in calls if c[0] == "AppendToTimeline"]
    check("with no segments the original is placed whole at the first frame and read back, no source range",
          len(a5) == 1 and a5[0].GetStart() == p.timeline.start and app and "startFrame" not in app[0][1][0]
          and any("read back True" in d for d in (g.get("result") or {}).get("done", [])), (calls, a5))
    calls = []
    p = Project(calls)
    p.timeline.tracks["audio"] = 6
    p.timeline.items[("audio", 5)] = [Item("someone_elses_bed.wav", p.timeline.start, 720, kind="audio")]
    g = run(substitute(console_src([]), [("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
                                         ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {mf!r}  # __MUSIC_FIT__")]),
            Resolve(calls, p), "mcp")
    check("a clip already on A5 is never placed over and nothing is deleted",
          len(p.timeline.items[("audio", 5)]) == 1 and not [c for c in calls if c[0] in ("AppendToTimeline", "ImportMedia")],
          calls)
    raw = open(CONSOLE, encoding="utf-8").read()
    check("music_fit.py's splice points are in the template",
          "MUSIC_FIT = {}  # __MUSIC_FIT__" in raw and "\nPLACE_MUSIC_FIT = False" in raw)

    print("resolve-production-console.py — PLACE_MUSIC_ELEMENTS, MUSIC_FAMILY, FAIRLIGHT_PRESET (composer.py console)")
    # (2026-11-05) composer.py no longer sends the alt mix (.full.wav) or the length family: both are Python previews
    els = [{"file": "/jobs/fx/06-music/compose/fx.layer.wav", "track": 6, "name": "A6 music", "color": "Purple",
            "enabled": True, "role": "composed layer"},
           {"file": "/jobs/fx/06-music/compose/fx.layer.stem-impact.wav", "track": 7, "name": "STEM impact (composed)",
            "color": "Navy", "enabled": False, "role": "stem"}]
    fam = []
    mk = [(6, "Purple", "Cue M1 establish", "warm · withhold", 96, ""),
          (240, "Green", "Hit H3 downbeat", "hard · window 0 to +42 ms, never early", 1, '{"hit": "H3", "window_ms": [0, 41.7]}')]
    for mode in ("mcp", "console"):
        calls = []
        p = Project(calls)
        p.timeline.tracks["audio"] = 6
        src = substitute(console_src(mk), [("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
                                            ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {dict(mf, color='Blue')!r}  # __MUSIC_FIT__"),
                                            ("\nPLACE_MUSIC_ELEMENTS = False", "\nPLACE_MUSIC_ELEMENTS = True"),
                                            ("MUSIC_ELEMENTS = []  # __MUSIC_ELEMENTS__", f"MUSIC_ELEMENTS = {els!r}  # __MUSIC_ELEMENTS__"),
                                            ("MUSIC_FAMILY = []  # __MUSIC_FAMILY__", f"MUSIC_FAMILY = {fam!r}  # __MUSIC_FAMILY__"),
                                            ('FAIRLIGHT_PRESET = ""', 'FAIRLIGHT_PRESET = "Cine Music"')])
        g = run(src, Resolve(calls, p), mode)
        tl = p.first
        a5, a6, a7 = (tl.GetItemListInTrack("audio", i) for i in (5, 6, 7))
        check(f"[{mode}] the original's segments on A5, the composed layer on A6, a stem on a new stereo track A7, "
              f"named — and no alt mix track",
              len(a5) == 2 and len(a6) == 1 and len(a7) == 1 and tl.GetTrackName("audio", 7) == "STEM impact (composed)"
              and tl.subtypes.get(("audio", 7)) == "stereo" and not tl.GetItemListInTrack("audio", 8), calls)
        check(f"[{mode}] the stem track is disabled, the layer's is not (the mix is never doubled)",
              tl.GetIsTrackEnabled("audio", 7) is False and tl.GetIsTrackEnabled("audio", 6) is True)
        check(f"[{mode}] clip colours by origin: the original's segments Blue, the layer Purple, the stem Navy",
              all(it.GetClipColor() == "Blue" for it in a5) and a6[0].GetClipColor() == "Purple"
              and a7[0].GetClipColor() == "Navy")
        check(f"[{mode}] the cue marker spans its cue and the hit marker carries its window as custom data",
              tl.markers[6]["duration"] == 96 and "window_ms" in tl.markers[240]["customData"], tl.markers)
        check(f"[{mode}] no length-family timeline is made (the family is a preview), and the cut timeline stays current",
              not [c for c in calls if c[0] == "CreateEmptyTimeline"] and not p.made and p.timeline is tl, calls)
        check(f"[{mode}] the named Fairlight preset is applied because Resolve lists it",
              ("ApplyFairlightPresetToCurrentTimeline", "Cine Music") in calls)
        n_imp = sum(1 for c in calls if c[0] == "ImportMedia")
        g = run(src, Resolve(calls, p), mode)
        check(f"[{mode}] run again: nothing imported twice, no timeline made",
              sum(1 for c in calls if c[0] == "ImportMedia") == n_imp and not p.made)
    raw = open(CONSOLE, encoding="utf-8").read()
    check("composer.py's splice points are in the template",
          "MUSIC_ELEMENTS = []  # __MUSIC_ELEMENTS__" in raw and "MUSIC_FAMILY = []  # __MUSIC_FAMILY__" in raw
          and 'FAIRLIGHT_PRESET = ""' in raw and "\nPLACE_MUSIC_ELEMENTS = False" in raw)

    print("resolve-production-console.py — the story map as markers (soundoff.py console)")
    sys.path.insert(0, HERE)
    import soundoff as SOF
    sj = tempfile.mkdtemp(prefix="soundoff-job-")
    os.makedirs(os.path.join(sj, "09-qa", "soundoff"))
    json.dump({"version": 1, "mode": "full", "windows": "manual", "beats": [
        {"id": "HOOK", "n": 1, "t0": 0.0, "t1": 3.0, "shows": "hands on a floured bench", "carries": "Y"},
        {"id": "S1", "n": 2, "t0": 3.0, "t1": 6.0, "shows": "the door opens", "carries": "N", "fix": "an insert of the price"},
        {"id": "CTA", "n": 3, "t0": 6.0, "t1": 10.0, "shows": "", "carries": ""}]},
        open(os.path.join(sj, "09-qa", "soundoff", "STORY-MAP.json"), "w"))
    ssrc = open(SOF.console_copy(sj), encoding="utf-8").read()
    for mode in ("mcp", "console"):
        calls = []
        p = Project(calls)
        g = run(ssrc, Resolve(calls, p), mode)
        mk = p.timeline.markers
        check(f"[{mode}] one duration marker per beat, coloured Green / Red / Blue by what the picture carries",
              sorted(mk) == [0, 72, 144] and mk[72]["color"] == "Red" and mk[72]["duration"] == 72
              and mk[144]["color"] == "Blue" and "fix: an insert" in mk[72]["note"], mk)
        check(f"[{mode}] and nothing else changes: no track added", not any(c[0] == "AddTrack" for c in calls), calls)

    print("resolve-production-console.py — APPLY_GRADE_PLAN (grade_luts.py plan --console)")
    for mode in ("mcp", "console"):
        calls = []
        tl = grade_timeline(calls)
        p = Project(calls, timeline=tl)
        g = run(grade_src(grade_plan("drama")), Resolve(calls, p), mode)
        rep = (g.get("result") or {}).get("grade") or {}
        it = {i.name: i for i in tl.items[("video", 1)]}
        s1, s2, s3, s4 = (it["S1_kling_v1.mp4"], it["S2_kling_v1.mp4"], it["S3 renamed in the bin"],
                          it["S4_seed_v1.mp4"])
        check(f"[{mode}] a colour group per model; the fitted model's LUT reads back on its pre-clip graph, the "
              f"unfitted one is reported, not assumed",
              rep.get("groups", {}).get("MODEL kling3_0") == "LUT read back"
              and "did NOT read back" in rep.get("groups", {}).get("MODEL seedance_2_5", ""), rep.get("groups"))
        check(f"[{mode}] an ungraded clip gets the template, its nodes switched, the look LUT and the CDL on node 1",
              ("ApplyGradeFromDRX", "/grades/clip-template.drx", 0) in calls and s1.graph.enabled == [True, False, True, True]
              and s1.graph.luts[2] == "MCP/cine_phone_60.cube" and s1.cdl and s1.cdl["NodeIndex"] == "1"
              and s1.cdl["Slope"] == "0.9700 1.0000 1.0300", (s1.graph.__dict__, s1.cdl))
        check(f"[{mode}] a clip with a grade of its own is never overwritten by the template",
              s2.graph.tools == [["Primary Balance"]] and s2.graph.labels == [""]
              and any("S2_kling_v1.mp4" in x for x in rep.get("problems", [])), (s2.graph.__dict__, rep.get("problems")))
        check(f"[{mode}] 4 unlabelled nodes are not the template: left alone, matched by its file name all the same",
              s3.graph.enabled == [True] * 4 and s3.graph.luts == [""] * 4 and s3.group and
              any("S3_seed_v1.mp4" in x and "layout" in x for x in rep.get("problems", [])), rep.get("problems"))
        check(f"[{mode}] a product shot on the template keeps look and texture off",
              s4.graph.enabled == [True, False, False, False] and s4.graph.luts[2] == "", s4.graph.__dict__)
        check(f"[{mode}] every clip is assigned to its model's group and read back",
              all(i.group and i.group.GetName() == grade_plan()["clips"][k]["group"]
                  for k, i in (("S1_kling_v1.mp4", s1), ("S2_kling_v1.mp4", s2), ("S3_seed_v1.mp4", s3),
                               ("S4_seed_v1.mp4", s4))), [(i.name, i.group and i.group.GetName()) for i in (s1, s2, s3, s4)])
        check(f"[{mode}] a clip outside the plan and a planned clip not on the timeline are both named; the "
              f"dissolve is neither",
              rep.get("unplanned") == ["someone_elses_title.mov"] and rep.get("not_on_timeline") == ["S9_missing_v1.mp4"],
              (rep.get("unplanned"), rep.get("not_on_timeline")))
        check(f"[{mode}] drama: the timeline's 0-node graph gets the timeline template, vignette on, film look off",
              tl.graph.labels == ["vignette", "film_look"] and tl.graph.enabled == [True, False]
              and rep.get("timeline") == {"vignette": True, "film_look": False}, (tl.graph.__dict__, rep.get("timeline")))
        check(f"[{mode}] the grade copy adds no track, lane or marker",
              not any(c[0] in ("AddTrack", "SetTrackName", "AddMarker") for c in calls), [c[0] for c in calls])
    calls = []
    tl = grade_timeline(calls)
    pa = grade_plan("ads"); pa.pop("timeline_drx")
    g = run(grade_src(pa), Resolve(calls, Project(calls, timeline=tl)), "mcp")
    rep = (g.get("result") or {}).get("grade") or {}
    check("ads: no timeline template wanted, none applied, and no complaint about it",
          tl.graph.GetNumNodes() == 0 and not any("timeline graph" in x for x in rep.get("problems", [])), rep)
    # (v2.48.0, project switch finish-texture) an ads plan that lifts C2 carries texture and the vignette, plus a
    # top-level `lifted` record: the console applies the nodes as planned and the extra key changes nothing else
    calls = []
    tl = grade_timeline(calls)
    pf = grade_plan("ads")
    for k in ("S1_kling_v1.mp4", "S2_kling_v1.mp4", "S3_seed_v1.mp4"):
        pf["clips"][k]["nodes"]["texture"] = True
    pf["timeline"]["vignette"] = True
    pf["lifted"] = {"finish-texture": {"rule": "grade-finish C2", "texture": ["S1_kling_v1.mp4"], "vignette": True,
                                       "lifted": "lifted by project switch `finish-texture` (a film look agreed)"}}
    g = run(grade_src(pf), Resolve(calls, Project(calls, timeline=tl)), "mcp")
    rep = (g.get("result") or {}).get("grade") or {}
    s1 = {i.name: i for i in tl.items[("video", 1)]}["S1_kling_v1.mp4"]
    check("ads with finish-texture lifted: the texture node and the timeline vignette go on as planned, film look off",
          s1.graph.enabled == [True, False, True, True] and rep.get("timeline") == {"vignette": True, "film_look": False},
          (s1.graph.__dict__, rep.get("timeline")))
    calls = []
    g = run(console_src(), Resolve(calls, Project(calls)), "mcp")
    check("the shipped template leaves the grade off (GRADE_PLAN empty, APPLY_GRADE_PLAN False)",
          "grade" not in (g.get("result") or {}) and not any(c[0] in ("AddColorGroup", "SetLUT") for c in calls), calls)

    print("resolve-production-console.py — INVENTORY_TEMPLATES and FUSION_TITLE_SPIKE (house rule C5, C7)")
    import zipfile
    troot, ofx = os.path.join(td, "Templates"), os.path.join(td, "OFX")
    for d in ("Edit/Titles", "Edit/Transitions", "Edit/Generators"):
        os.makedirs(os.path.join(troot, d))
    os.makedirs(os.path.join(ofx, "Sapphire.ofx.bundle"))
    for f in ("Edit/Titles/Lower Third Clean.setting", "Edit/Transitions/Whip Pan Left.setting"):
        open(os.path.join(troot, f), "w").write("{ Tools = {} }")
    with zipfile.ZipFile(os.path.join(troot, "Pack.drfx"), "w") as z:
        z.writestr("Edit/Transitions/Light Leak 04.setting", "{}")
        z.writestr("Edit/Titles/Cinematic Title 07.setting", "{}")
    inv_path = os.path.join(td, "resolve-inventory.json")

    def toggles_src(**kw):
        pairs = []
        if kw.get("inventory"):
            pairs += [("\nINVENTORY_TEMPLATES = False", "\nINVENTORY_TEMPLATES = True"),
                      ('OFX_DIRS = ["/Library/OFX/Plugins", r"C:\\Program Files\\Common Files\\OFX\\Plugins", "/usr/OFX/Plugins"]',
                       f"OFX_DIRS = [{ofx!r}]"),
                      # ⛔ Keep the walk inside the fixture. The script also reads this machine's own template
                      # folders (the user's, the system's, the app's), and on a Mac with Resolve installed those
                      # hold hundreds of real templates: an exact list can only be true of the fixture
                      # [measured 2026-11-10 · this Mac: the two checks below failed on the machine's templates].
                      ('    _roots += [("extra", str(_r)) for _r in INVENTORY_EXTRA_ROOTS]\n',
                       '    _roots = [_r for _r in _roots if _r[0] == "fusion"] + '
                       '[("extra", str(_r)) for _r in INVENTORY_EXTRA_ROOTS]\n')]
            if kw.get("path"):
                pairs.append(('r"REPLACE-WITH-A-FOLDER/resolve-inventory.json"', repr(kw["path"])))
        if kw.get("spike"):
            pairs.append(("\nFUSION_TITLE_SPIKE = False", "\nFUSION_TITLE_SPIKE = True"))
            if kw.get("title"):
                pairs.append(('SPIKE_TITLE = "Text+"', f"SPIKE_TITLE = {kw['title']!r}"))
        return substitute(open(CONSOLE, encoding="utf-8").read(), pairs)
    calls = []
    rv = Resolve(calls, Project(calls)); rv.templates = troot
    run(toggles_src(inventory=True, path=inv_path), rv, "console")
    inv = json.load(open(inv_path, encoding="utf-8")) if os.path.isfile(inv_path) else {}
    got = sorted((t["kind"], t["name"], t["source"]) for t in inv.get("templates", []))
    check("[console] the inventory lists loose templates and the ones inside a .drfx, by kind, and the OFX bundles",
          got == [("title", "Cinematic Title 07", "drfx:Pack.drfx"), ("title", "Lower Third Clean", "fusion"),
                  ("transition", "Light Leak 04", "drfx:Pack.drfx"), ("transition", "Whip Pan Left", "fusion")]
          and inv.get("ofx") == ["Sapphire"] and inv.get("resolve") == "21.1.1"
          and inv.get("roots") == [os.path.realpath(troot)],
          {**{k: v for k, v in inv.items() if k != "templates"}, "templates": len(got)})
    check("[console] the inventory adds nothing to the project (the lanes are the ENSURE_* toggles' own)",
          not any(c[0] in ("AddMarker", "SetLUT", "CreateEmptyTimeline", "InsertFusionTitleIntoTimeline",
                           "SetCurrentTimeline", "SetSetting") for c in calls), [c[0] for c in calls])
    import motion_qa as MQ
    tg = MQ.tag_inventory(inv_path)
    check("motion_qa.py inventory tags it: whip and light families, the titles the default engine once proven (C7)",
          tg["count"] == {"title": 2, "transition/light": 1, "transition/whip": 1}
          and all("C7" in t["use"] for t in tg["templates"] if t["kind"] == "title"), tg["count"])
    calls = []
    g = run(toggles_src(inventory=True), Resolve(calls, Project(calls)), "mcp")
    check("[mcp] the run_script sandbox has no os: the inventory says where to run it, and nothing breaks",
          "filesystem" in str(((g.get("result") or {}).get("inventory") or {}).get("error")), (g.get("result") or {}).get("inventory"))
    for mode in ("mcp", "console"):
        calls = []
        p = Project(calls)
        cut = p.timeline
        before = list(cut.items[("video", 1)])
        g = run(toggles_src(spike=True), Resolve(calls, p), mode)
        sp = (g.get("result") or {}).get("spike") or {}
        check(f"[{mode}] the title spike: a scratch 1080×1920 timeline, the text set and read back → PROVEN",
              sp.get("verdict") == "PROVEN" and sp.get("resolution") == ["1080", "1920"]
              and sp.get("text_inputs") == [{"tool": "Template", "was": "Custom Title", "reads_back": True}], sp)
        check(f"[{mode}] ... and the cut is untouched: the title went on the scratch timeline, and the current "
              f"timeline is the cut again",
              p.timeline is cut and cut.items[("video", 1)] == before and len(p.made) == 1
              and ("InsertFusionTitleIntoTimeline", cut.name, "Text+") not in calls and sp.get("returned_to") == cut.name,
              (calls, sp))
    calls = []
    g = run(toggles_src(spike=True, title="Cinematic Title 07"), Resolve(calls, Project(calls)), "mcp")
    sp = (g.get("result") or {}).get("spike") or {}
    check("a marketplace title whose text sits behind a macro control is NOT PROVEN, and its tools are named",
          sp.get("verdict") == "NOT PROVEN" and any("Macro1" in x for x in sp.get("problems", [])), sp)
    calls = []
    g = run(toggles_src(spike=True, title="No Such Title"), Resolve(calls, Project(calls)), "mcp")
    sp = (g.get("result") or {}).get("spike") or {}
    check("a title name the Effects Library does not have is NOT PROVEN, with the name in the problem",
          sp.get("verdict") == "NOT PROVEN" and any("No Such Title" in x for x in sp.get("problems", [])), sp)

    print("the gate reads both scripts the way it is meant to")
    sys.path.insert(0, HERE)
    import gate as G
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": render_src(out)})
    check("render-mp4.py through run_script → ask (render settings), never deny",
          d["decision"] == "ask" and "render settings" in d["reason"], d)
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": console_src(beats)})
    check("resolve-production-console.py through run_script → pass with context (an edit, nothing hazardous)",
          d["decision"] == "pass" and "Resolve edit" in d["context"], d)
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": toggles_src(spike=True)})
    check("the title spike through run_script → deny, house rule 8 (it inserts a title and sets its words by script)",
          d["decision"] == "deny" and "computer-control rule" in d["reason"], d)
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": substitute(console_src(music), [
        ("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"), ("MUSIC_FIT = {}  # __MUSIC_FIT__", f"MUSIC_FIT = {mf!r}  # __MUSIC_FIT__")])})
    check("its music copy through run_script → pass (an import and an append: nothing deleted)",
          d["decision"] == "pass" and "Resolve edit" in d["context"], d)
    d = G.decide("mcp__DaVinci_Resolve__run_script", {"script": grade_src(grade_plan("drama"))})
    check("its grade copy through run_script → pass (an edit: no render, no delete, nothing opaque)",
          d["decision"] == "pass" and "Resolve edit" in d["context"], d)

    print(f"\n{'OK' if not fails else 'FAILED'} — {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
