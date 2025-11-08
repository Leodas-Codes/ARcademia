#!/usr/bin/env python3
"""
ARcademia — Desktop Viewer & Virtual AR Preview (Open3D GUI) — main.py
---------------------------------------------------------------------
• Open3D 0.18/0.19 on Python 3.10+
• Loads STL/OBJ from ./cad_files
• Virtual AR Preview window (no AR glasses required)
• UDP streamer left in place for future, but not used by default
• Safe across minor GUI API differences (0.18 vs 0.19)
Hotkeys: B back-face | L axes | R frame | S screenshot | DEL remove
"""
from __future__ import annotations
import json
import socket
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: pyttsx3 not available. Voice-over features disabled.")

# ---------- User config ----------
MODELS_DIR = Path("./cad_files")
AR_IP_DEFAULT = "192.168.0.10"
AR_PORT_DEFAULT = 51234
UDP_CHUNK = 60000
SUPPORTED_EXTS = {".stl", ".obj"}
# ---------------------------------


# ---------- Model Analysis Helper ----------
def analyze_model(mesh: o3d.geometry.TriangleMesh, name: str) -> Dict:
    """Analyze 3D model and extract dimensional and geometric features."""
    bbox = mesh.get_axis_aligned_bounding_box()
    extent = bbox.get_extent()
    center = bbox.get_center()
    
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    
    analysis = {
        "name": name,
        "vertices": len(vertices),
        "triangles": len(triangles),
        "dimensions": {
            "width": float(extent[0]),
            "height": float(extent[1]),
            "depth": float(extent[2]),
        },
        "volume": float(mesh.get_volume()) if mesh.is_watertight() else 0,
        "surface_area": float(mesh.get_surface_area()),
        "is_watertight": mesh.is_watertight(),
        "center": [float(c) for c in center],
    }
    return analysis


def generate_description(analysis: Dict) -> str:
    """Generate natural language description of the 3D model."""
    name = analysis["name"]
    verts = analysis["vertices"]
    tris = analysis["triangles"]
    dims = analysis["dimensions"]
    
    description = f"This is {name}. "
    description += f"The model contains {verts:,} vertices and {tris:,} triangular faces. "
    
    description += f"Its dimensions are: "
    description += f"width {dims['width']:.2f} units, "
    description += f"height {dims['height']:.2f} units, "
    description += f"and depth {dims['depth']:.2f} units. "
    
    if analysis['is_watertight']:
        volume = analysis['volume']
        description += f"This is a watertight solid with a volume of {volume:.2f} cubic units. "
    else:
        description += "This is a surface model, not a solid. "
    
    area = analysis['surface_area']
    description += f"The total surface area is {area:.2f} square units. "
    
    return description


class App:
    def __init__(self) -> None:
        # state
        self.models_dir: Path = MODELS_DIR
        self.entries: Dict[str, Path] = {}
        self.loaded: Dict[str, o3d.geometry.TriangleMesh] = {}
        self.selected: Optional[str] = None
        self.show_axes: bool = True
        self.double_sided: bool = True
        
        # TTS engine
        self.tts_engine = None
        self.tts_thread = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)
            except Exception as e:
                print(f"TTS initialization failed: {e}")
                self.tts_engine = None

        # GUI init
        gui.Application.instance.initialize()
        self.window = gui.Application.instance.create_window("ARcademia VR Panel", 1280, 800)

        # 3D viewport
        self.scene_w = gui.SceneWidget()
        self.scene = rendering.Open3DScene(self.window.renderer)
        self.scene_w.scene = self.scene
        self.scene.set_background([0.05, 0.05, 0.07, 1.0])
        self.window.add_child(self.scene_w)

        # Right panel
        self.panel = gui.Vert(0, gui.Margins(8, 8, 8, 8))
        self.window.add_child(self.panel)

        # Layout
        em = self.window.theme.font_size
        panel_w = int(28 * em)

        def on_layout(_):
            r = self.window.content_rect
            self.scene_w.frame = gui.Rect(r.x, r.y, r.width - panel_w, r.height)
            self.panel.frame = gui.Rect(r.get_right() - panel_w, r.y, panel_w, r.height)

        self.window.set_on_layout(on_layout)

        # Folder + controls
        self.folder_label = gui.Label(self._folder_text())
        self.panel.add_child(self.folder_label)

        row = gui.Horiz()
        self.btn_choose = gui.Button("Choose Folder")
        self.btn_choose.set_on_clicked(self._choose_folder)
        row.add_child(self.btn_choose)

        self.btn_refresh = gui.Button("Refresh List")
        self.btn_refresh.set_on_clicked(self.refresh_list)
        row.add_child(self.btn_refresh)
        self.panel.add_child(row)

        # File list
        self.list = gui.ListView()
        self.list.set_on_selection_changed(self._on_select)
        self.panel.add_child(self.list)

        # Actions
        self.btn_display = gui.Button("Display Model")
        self.btn_display.set_on_clicked(self.display_selected)
        self.panel.add_child(self.btn_display)

        self.btn_add = gui.Button("Add To Scene")
        self.btn_add.set_on_clicked(self.add_selected)
        self.panel.add_child(self.btn_add)

        self.btn_remove = gui.Button("Remove Selected")
        self.btn_remove.set_on_clicked(self.remove_selected)
        self.panel.add_child(self.btn_remove)

        # AR / Preview section
        self.panel.add_child(gui.Label("AR / Preview"))
        row2 = gui.Horiz()
        self.ip_edit = gui.TextEdit()
        self.ip_edit.text_value = AR_IP_DEFAULT
        self.port_edit = gui.TextEdit()
        self.port_edit.text_value = str(AR_PORT_DEFAULT)
        row2.add_child(self.ip_edit)
        row2.add_child(self.port_edit)
        self.panel.add_child(row2)

        self.btn_preview = gui.Button("Virtual AR Preview")
        self.btn_preview.set_on_clicked(self.virtual_ar_preview)
        self.panel.add_child(self.btn_preview)

        # Voice-Over section
        self.panel.add_child(gui.Label("AI Voice-Over"))
        if self.tts_engine:
            self.btn_describe = gui.Button("🔊 Describe Model")
            self.btn_describe.set_on_clicked(self.describe_model)
            self.panel.add_child(self.btn_describe)
            
            self.btn_describe_all = gui.Button("🔊 Describe Scene")
            self.btn_describe_all.set_on_clicked(self.describe_scene)
            self.panel.add_child(self.btn_describe_all)
        else:
            self.panel.add_child(gui.Label("(TTS not available)"))

        # View toggles
        self.chk_axes = gui.Checkbox("Show Axes")
        self.chk_axes.checked = True
        self.chk_axes.set_on_checked(lambda v: self._set_axes(v))
        self.panel.add_child(self.chk_axes)

        self.chk_ds = gui.Checkbox("Double-sided (no cull)")
        self.chk_ds.checked = True
        self.chk_ds.set_on_checked(self._set_double_sided)
        self.panel.add_child(self.chk_ds)

        # Stats
        self.stats = gui.Label("Stats: —")
        self.panel.add_child(self.stats)

        # Keyboard shortcuts
        self.window.set_on_key(self._on_key)

        # Scene utilities
        self.scene.show_axes(self.show_axes)
        self._frame_default()

        # Populate list now
        self.refresh_list()

    # ---------- small compat helpers ----------
    def _redraw(self) -> None:
        """Safely request a redraw across Open3D minor versions."""
        if hasattr(self.window, "post_redraw"):
            self.window.post_redraw()

    def _screenshot_current_scene(self) -> o3d.geometry.Image:
        """Works on 0.18 (callback) and 0.19+ (direct)."""
        if hasattr(self.scene, "render_to_image"):
            return self.scene.render_to_image()
        image_box = {}

        def _cb(img):
            image_box["img"] = img

        self.scene.scene.render_to_image(_cb)
        t0 = time.time()
        while "img" not in image_box and time.time() - t0 < 2.0:
            time.sleep(0.01)
        return image_box.get("img")

    # ---------- UI helpers ----------
    def _folder_text(self) -> str:
        return f"Folder:\n{self.models_dir}"

    def _material(self) -> rendering.MaterialRecord:
        m = rendering.MaterialRecord()
        m.shader = "defaultLit"
        try:
            m.double_sided = self.double_sided
        except Exception:
            pass
        try:
            m.cull_mode = (
                rendering.MaterialRecord.CullMode.NONE
                if self.double_sided
                else rendering.MaterialRecord.CullMode.BACK
            )
        except Exception:
            pass
        return m

    # ---------- Folder & list ----------
    def _scan(self) -> List[str]:
        if not self.models_dir.exists():
            return []
        return [
            p.name
            for p in sorted(self.models_dir.iterdir())
            if p.suffix.lower() in SUPPORTED_EXTS
        ]

    def refresh_list(self) -> None:
        items = self._scan()
        self.list.set_items(items)
        self.entries = {name: (self.models_dir / name) for name in items}
        self.folder_label.text = self._folder_text()
        self._redraw()

    def _on_select(self, idx: int) -> None:
        items = self.list.get_items()
        if 0 <= idx < len(items):
            self.selected = items[idx]

    def _choose_folder(self) -> None:
        dlg = gui.FileDialog(gui.FileDialog.OPEN_DIR, "Select Models Folder", self.window.theme)
        dlg.set_on_cancel(lambda: self.window.close_dialog())

        def _ok(path):
            self.window.close_dialog()
            self.models_dir = Path(path)
            self.loaded.clear()
            self.selected = None
            self.refresh_list()

        dlg.set_on_done(_ok)
        self.window.show_dialog(dlg)

    # ---------- Load & display ----------
    def _load_mesh(self, path: Path) -> Optional[o3d.geometry.TriangleMesh]:
        try:
            mesh = o3d.io.read_triangle_mesh(str(path))
            if mesh is None or len(mesh.triangles) == 0:
                raise ValueError("Empty/invalid mesh")
            mesh.compute_vertex_normals()
            return mesh
        except Exception as e:
            self._toast(f"Failed to load: {path.name}\n{e}")
            return None

    def _add_geom(self, name: str, mesh: o3d.geometry.TriangleMesh) -> None:
        if name in self.scene.get_geometry_names():
            self.scene.remove_geometry(name)
        self.scene.add_geometry(name, mesh, self._material())
        self._redraw()

    def display_selected(self) -> None:
        if not self.selected:
            self._toast("Select a model first")
            return
        for g in list(self.scene.get_geometry_names()):
            self.scene.remove_geometry(g)
        self.scene.show_axes(self.show_axes)
        p = self.entries.get(self.selected)
        if not p:
            return
        mesh = self._load_mesh(p)
        if not mesh:
            return
        self.loaded = {self.selected: mesh}
        self._add_geom(self.selected, mesh)
        self._frame_scene()
        self._update_stats()
        self._toast(f"Displayed {self.selected}")

    def add_selected(self) -> None:
        if not self.selected:
            self._toast("Select a model first")
            return
        p = self.entries.get(self.selected)
        if not p:
            return
        mesh = self.loaded.get(self.selected)
        if mesh is None:
            mesh = self._load_mesh(p)
            if not mesh:
                return
            self.loaded[self.selected] = mesh
        self._add_geom(self.selected, mesh)
        self._frame_scene()
        self._update_stats()
        self._toast(f"Added {self.selected}")

    def remove_selected(self) -> None:
        if not self.selected:
            return
        if self.selected in self.scene.get_geometry_names():
            self.scene.remove_geometry(self.selected)
        self.loaded.pop(self.selected, None)
        self._update_stats()
        self._redraw()

    def _frame_scene(self) -> None:
        bbox = self.scene.bounding_box
        self.scene_w.setup_camera(60.0, bbox, bbox.get_center())

    def _frame_default(self) -> None:
        bbox = o3d.geometry.AxisAlignedBoundingBox([-1, -1, -1], [1, 1, 1])
        self.scene_w.setup_camera(60.0, bbox, [0, 0, 0])

    def _update_stats(self) -> None:
        v = t = 0
        for name in self.scene.get_geometry_names():
            m = self.loaded.get(name)
            if m is not None:
                v += len(m.vertices)
                t += len(m.triangles)
        self.stats.text = f"Stats: Verts={v:,}  Tris={t:,}"

    # ---------- Merge for preview/stream ----------
    def _merge(self) -> Optional[o3d.geometry.TriangleMesh]:
        meshes = [self.loaded[n] for n in self.scene.get_geometry_names() if n in self.loaded]
        if not meshes:
            return None
        out = o3d.geometry.TriangleMesh()
        for m in meshes:
            out += m
        out.compute_vertex_normals()
        return out

    # ---------- Virtual AR Preview (no glasses needed) ----------
    def virtual_ar_preview(self) -> None:
        mesh = self._merge()
        if mesh is None:
            self._toast("No models to preview")
            return

        preview = gui.Application.instance.create_window("AR Virtual Preview", 1000, 700)
        sw = gui.SceneWidget()
        preview.add_child(sw)
        scene = rendering.Open3DScene(preview.renderer)
        sw.scene = scene
        scene.set_background([0.12, 0.12, 0.12, 1.0])

        ground = o3d.geometry.TriangleMesh.create_box(5, 0.02, 5)
        ground.translate([-2.5, -0.02, -2.5])
        ground.paint_uniform_color([0.35, 0.35, 0.37])
        mat_floor = rendering.MaterialRecord()
        mat_floor.shader = "defaultLit"
        scene.add_geometry("__ground__", ground, mat_floor)

        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        try:
            mat.double_sided = True
        except Exception:
            pass
        scene.add_geometry("__model__", mesh, mat)

        bbox = mesh.get_axis_aligned_bounding_box()
        center = bbox.get_center()
        sw.setup_camera(60.0, bbox, center)

        help_lab = gui.Label(
            "Virtual AR Preview\nLeft drag: orbit  |  Right drag: pan  |  Wheel: zoom"
        )
        preview.add_child(help_lab)

        self._toast("Virtual AR Preview opened")

    # ---------- Toggles & keys ----------
    def _set_axes(self, on: bool) -> None:
        self.show_axes = on
        self.scene.show_axes(on)
        self._redraw()

    def _set_double_sided(self, on: bool) -> None:
        self.double_sided = on
        for name in list(self.scene.get_geometry_names()):
            if name in self.loaded:
                self.scene.modify_geometry_material(name, self._material())
        self._redraw()

    def _screenshot(self) -> None:
        out = Path("screenshots")
        out.mkdir(parents=True, exist_ok=True)
        fn = out / f"shot_{int(time.time())}.png"
        img = self._screenshot_current_scene()
        if img is not None:
            o3d.io.write_image(str(fn), img)
            self._toast(f"Saved {fn}")
        else:
            self._toast("Screenshot failed")

    def _on_key(self, ev):
        if ev.type != gui.KeyEvent.DOWN:
            return gui.Widget.EventCallbackResult.IGNORED
        k = ev.key
        if k in (ord("B"), ord("b")):
            self.chk_ds.checked = not self.chk_ds.checked
            self._set_double_sided(self.chk_ds.checked)
            return gui.Widget.EventCallbackResult.HANDLED
        if k in (ord("L"), ord("l")):
            self.chk_axes.checked = not self.chk_axes.checked
            self._set_axes(self.chk_axes.checked)
            return gui.Widget.EventCallbackResult.HANDLED
        if k in (ord("R"), ord("r")):
            self._frame_scene()
            return gui.Widget.EventCallbackResult.HANDLED
        if k in (ord("S"), ord("s")):
            self._screenshot()
            return gui.Widget.EventCallbackResult.HANDLED
        if k == gui.KeyName.DELETE:
            self.remove_selected()
            return gui.Widget.EventCallbackResult.HANDLED
        return gui.Widget.EventCallbackResult.IGNORED

    # ---------- Voice-Over Methods ----------
    def _speak(self, text: str) -> None:
        """Speak text using TTS in a separate thread to avoid blocking GUI."""
        if not self.tts_engine:
            self._toast("TTS not available")
            return
        
        def speak_thread():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e}")
        
        if self.tts_thread and self.tts_thread.is_alive():
            self._toast("Voice-over already playing...")
            return
        
        self.tts_thread = threading.Thread(target=speak_thread, daemon=True)
        self.tts_thread.start()

    def describe_model(self) -> None:
        """Generate and speak description of the selected model."""
        if not self.selected:
            self._toast("Select a model first")
            return
        
        if self.selected not in self.loaded:
            self._toast("Model not loaded yet")
            return
        
        mesh = self.loaded[self.selected]
        analysis = analyze_model(mesh, self.selected)
        description = generate_description(analysis)
        
        self._toast(f"Describing {self.selected}...")
        self._speak(description)

    def describe_scene(self) -> None:
        """Generate and speak description of all models in the scene."""
        geom_names = [n for n in self.scene.get_geometry_names() if n in self.loaded]
        
        if not geom_names:
            self._toast("No models in scene")
            return
        
        if len(geom_names) == 1:
            self.describe_model()
            return
        
        descriptions = []
        descriptions.append(f"This scene contains {len(geom_names)} models. ")
        
        for name in geom_names:
            mesh = self.loaded[name]
            analysis = analyze_model(mesh, name)
            desc = f"{name} has {analysis['vertices']:,} vertices, "
            desc += f"{analysis['triangles']:,} faces, "
            desc += f"and dimensions of {analysis['dimensions']['width']:.2f} by "
            desc += f"{analysis['dimensions']['height']:.2f} by {analysis['dimensions']['depth']:.2f} units. "
            descriptions.append(desc)
        
        full_description = " ".join(descriptions)
        self._toast(f"Describing {len(geom_names)} models...")
        self._speak(full_description)

    def _toast(self, msg: str, dur: float = 1.5) -> None:
        gui.Application.instance.post_toast(self.window, msg, dur)


# ---------- UDP helpers (for future AR use) ----------
def _pack_mesh(mesh: o3d.geometry.TriangleMesh) -> bytes:
    v = np.asarray(mesh.vertices, dtype=np.float32).reshape(-1).tolist()
    t = np.asarray(mesh.triangles, dtype=np.int32).reshape(-1).tolist()
    return json.dumps({"type": "mesh", "vertices": v, "triangles": t, "ts": time.time()}).encode()


def send_mesh_udp(mesh: o3d.geometry.TriangleMesh, ip: str, port: int, chunk: int) -> int:
    data = _pack_mesh(mesh)
    total = len(data)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        header = b"ARC\x01"
        parts = (total + chunk - 1) // chunk
        for i in range(parts):
            part = data[i * chunk : (i + 1) * chunk]
            pkt = header + i.to_bytes(2, "big") + parts.to_bytes(2, "big") + part
            sock.sendto(pkt, (ip, port))
    finally:
        sock.close()
    return total


if __name__ == "__main__":
    try:
        app = App()
        gui.Application.instance.run()
    except Exception as e:
        import traceback, sys
        traceback.print_exc()
        sys.exit(1)
