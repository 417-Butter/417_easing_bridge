# Author: 417_Butter
import csc
import json
import socket
import struct
import math
import numpy as np
import common.selection_operations as so
import os
import datetime
import time
import sys
import platform
import tempfile

# ==============================================================
# ホットキー自動登録 (Win / Mac / Linux 対応版)
# ==============================================================
def setup_initial_hotkey():
    # INI書き込み用のコマンド名（半角スペースは %20 にエスケープ）
    target_command_ini = "Easing%20Bridge_417.Bake"  
    system = platform.system()
    
    # OSに合わせてホットキーを動的に変更
    if system == 'Darwin':
        target_hotkey = "Cmd+B"   # Macの場合は Command+B
    else:
        target_hotkey = "Ctrl+B"  # Win/Linuxの場合は Ctrl+B

    # 1. OSごとに設定フォルダのパスを特定する
    if system == 'Windows':
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            return
        ini_dir = os.path.join(local_app_data, "Nekki Limited", "Cascadeur")
        
    elif system == 'Linux':
        ini_dir = os.path.join(os.path.expanduser('~'), ".local", "share", "Nekki Limited", "Cascadeur")
        
    elif system == 'Darwin': # Mac OS
        ini_dir = os.path.join(os.path.expanduser('~'), "Library", "Application Support", "Nekki Limited", "Cascadeur")
        if not os.path.exists(ini_dir):
            ini_dir = os.path.join(os.path.expanduser('~'), ".local", "share", "Nekki Limited", "Cascadeur")
            
    else:
        return # 未知のOSはスキップ

    # 2. iniファイルの存在確認
    ini_path = os.path.join(ini_dir, "Hotkey_settings.ini")
    if not os.path.exists(ini_path):
        return

    # 3. 登録処理
    with open(ini_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 既に登録済みの場合はスキップ、またはショートカットキーが他の機能で使われている場合もスキップ
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(target_command_ini + "="):
            return 
        
        # 既にCtrl+Bなどが他の機能に割り当てられているかチェック
        if "=" in stripped:
            key_assigned = stripped.split("=", 1)[1].strip()
            if key_assigned.lower() == target_hotkey.lower():
                print(f"[{target_hotkey}] は既に他の機能に割り当てられているため、自動登録をスキップしました。")
                return

    new_lines =[]
    section_found = False
    for line in lines:
        new_lines.append(line)
        if line.strip() == "[Commands]":
            section_found = True
            new_lines.append(f"{target_command_ini}={target_hotkey}\n")

    if not section_found:
        new_lines.append("\n[Commands]\n")
        new_lines.append(f"{target_command_ini}={target_hotkey}\n")

    with open(ini_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"[Easing Bridge_417.Bake] に[{target_hotkey}] を自動登録しました！(次回起動時から有効)")

try:
    setup_initial_hotkey()
except Exception:
    pass


# ==============================================================
# コマンド本体
# ==============================================================

def command_name():
    # ツール上の登録名
    return "Easing Bridge_417.Bake"

_log_buf = []

def log(msg):
    msg_str = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    _log_buf.append(msg_str)

def flush_log(gui_dir=None):
    try:
        if gui_dir and os.path.exists(gui_dir):
            log_file = os.path.join(gui_dir, 'easing_bridge_bake.log')
        else:
            temp_dir = tempfile.gettempdir()
            log_file = os.path.join(temp_dir, 'easing_bridge_bake.log')
            
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(_log_buf) + "\n")
        _log_buf.clear()
    except Exception:
        pass


# --------------------------------------------------------------
# 1. 外部GUIへのFetch機能
# --------------------------------------------------------------
def fetch_data_and_send(scene, host='127.0.0.1', port=65432):
    payload = {
        "command": "FETCH_RESULT",
        "frame_start": 0,
        "frame_end": 0,
        "layers":[],
        "frame_count": 0
    }

    def mod(model, update, sc):
        ls = model.layers_selector()
        lv = sc.layers_viewer()
        
        try:
            frames = ls.selection().frames_interval()
            payload["frame_start"] = frames.first
            payload["frame_end"] = frames.last
            payload["frame_count"] = frames.last - frames.first + 1
        except Exception:
            pass
            
        layer_ids = ls.all_included_layer_ids()
        for layer_id in layer_ids:
            layer = lv.layer(layer_id)
            obj_ids = layer.obj_ids
            payload["layers"].append({
                "layer_id": str(layer_id),
                "obj_ids":[str(obj_id) for obj_id in obj_ids]
            })

    # Modifyの名前も統一
    scene.modify("Easing Bridge_417.Fetch", mod)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((host, port))
            
            json_str = json.dumps(payload)
            payload_bytes = json_str.encode('utf-8')
            header = struct.pack(">I", len(payload_bytes))
            
            s.sendall(header + payload_bytes)
        return True
    except Exception as e:
        scene.error(f"[{command_name()}] Error connecting to GUI during Fetch: {e}")
        return False

# --------------------------------------------------------------
# 2. 外部GUIからのBakeカーブ取得機能
# --------------------------------------------------------------
def request_curve(scene, host='127.0.0.1', port=65432, silent=False):
    payload = {"command": "REQUEST_CURVE"}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((host, port))
            json_str = json.dumps(payload)
            payload_bytes = json_str.encode('utf-8')
            header = struct.pack(">I", len(payload_bytes))
            s.sendall(header + payload_bytes)
            data = s.recv(4)
            if len(data) < 4:
                if not silent: scene.error(f"[{command_name()}] Empty response from GUI")
                return None
            res_len = struct.unpack(">I", data)[0]
            res_data = b""
            while len(res_data) < res_len:
                chunk = s.recv(min(4096, res_len - len(res_data)))
                if not chunk:
                    break
                res_data += chunk
            return json.loads(res_data.decode('utf-8'))
    except Exception as e:
        if not silent:
            scene.error(f"[{command_name()}] Error receiving curve: {e}")
        return None

# --------------------------------------------------------------
# ヘルパー関数群（Bake補間用）
# --------------------------------------------------------------
def euler_to_quat(euler):
    cx = math.cos(euler[0] * 0.5)
    sx = math.sin(euler[0] * 0.5)
    cy = math.cos(euler[1] * 0.5)
    sy = math.sin(euler[1] * 0.5)
    cz = math.cos(euler[2] * 0.5)
    sz = math.sin(euler[2] * 0.5)
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return np.array([w, x, y, z])

def quat_to_euler(q):
    w, x, y, z = q
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return [roll, pitch, yaw]

def slerp(q1, q2, t):
    dot = np.sum(q1 * q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
    if dot > 0.9995:
        res = q1 + t * (q2 - q1)
        return res / np.linalg.norm(res)
    
    theta_0 = math.acos(dot)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    sin_theta_0 = math.sin(theta_0)
    
    s1 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s2 = sin_theta / sin_theta_0
    res = (s1 * q1) + (s2 * q2)
    return res / np.linalg.norm(res)

def interpolate_value(val_start, val_end, t, is_rot=False):
    if is_rot:
        try:
            trnsf_euler_start = csc.math.Rotation.to_euler_angles(val_start)
            trnsf_euler_end   = csc.math.Rotation.to_euler_angles(val_end)
            
            q1 = euler_to_quat(trnsf_euler_start)
            q2 = euler_to_quat(trnsf_euler_end)
            q_interp = slerp(q1, q2, t)
            new_euler = quat_to_euler(q_interp)
            
            for i in range(3):
                diff = new_euler[i] - trnsf_euler_start[i]
                if diff > math.pi: new_euler[i] -= 2*math.pi
                elif diff < -math.pi: new_euler[i] += 2*math.pi

            return csc.math.Rotation.from_euler(new_euler)
        except Exception as e:
            log(f"Interpolation error (Rotation): {e}")
            return val_start

    if isinstance(val_start, bool) or type(val_start) is bool:
        return bool(val_start if t < 0.5 else val_end)
    elif isinstance(val_start, int) and not isinstance(val_start, bool):
        return int(round(val_start + (val_end - val_start) * t))
    elif isinstance(val_start, float):
        return float(val_start + (val_end - val_start) * t)

    try:
        vs = np.array(val_start)
        ve = np.array(val_end)
        new_v = vs + (ve - vs) * t
        
        if isinstance(val_start, list):
            return list(new_v)
        elif isinstance(val_start, tuple):
            return tuple(new_v)
        elif 'Vector' in str(type(val_start)):
            return tuple(new_v)
        else:
            return new_v
    except Exception as e:
        log(f"Interpolation error (Value): {e}")

    return val_start


# --------------------------------------------------------------
# 3. メインの実行フロー (Fetch -> Bake)
# --------------------------------------------------------------
def run(scene):
    if not fetch_data_and_send(scene):
        return

    obj_ids = so.selected_obj_ids(scene)
    if len(obj_ids) == 0:
        scene.error("No objects selected")
        return

    curve_data = None
    max_retries = 3
    for attempt in range(max_retries):
        time.sleep(0.1) 
        curve_data = request_curve(scene, silent=(attempt < max_retries - 1))
        if curve_data and curve_data.get("command") == "CURVE_DATA":
            break
        log(f"Waiting for GUI response... (Attempt {attempt + 1}/{max_retries})")

    if not curve_data or curve_data.get("command") != "CURVE_DATA":
        scene.error(f"[{command_name()}] Invalid or missing curve data from GUI.")
        flush_log()
        return

    easing_table = curve_data.get("easing_table",[])
    gui_dir = curve_data.get("gui_dir")

    log(f"\n{'='*60}")
    log(f"BAKE START  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def mod(model, update, scene_updater, session):
        le = model.layers_editor()
        lv = scene.layers_viewer()
        mv = scene.model_viewer()
        beh_viewer = mv.behaviour_viewer()

        start_frame = model.layers_selector().selection().frames_interval().first
        end_frame   = model.layers_selector().selection().frames_interval().last
        frames = range(start_frame, end_frame + 1)

        if len(easing_table) < len(frames):
            scene.error("Easing table missing or too short!")
            flush_log(gui_dir)
            return

        ALL_POSSIBLE_NODES =[
            'Local Position', 'Position',
            'Local Rotation', 'Rotation',
            'Local Scale', 'Scale',
            'Projected AdditionalVector', 'AdditionalVector',
            'IK Direction', 'LocalDirection', 'Direction',
            'Twist', 'Distance', 'FOV', 'Fov', 'Roll', 'Focal Length'
        ]

        obj_data =[]
        for obj_id in obj_ids:
            obj_name = mv.get_object_name(obj_id) or "Unknown"
            log(f"\n--- Object: '{obj_name}' (id={obj_id}) ---")

            node_objects = {}
            for node in ALL_POSSIBLE_NODES:
                try:
                    obj = update.get_object_by_id(obj_id).root_group().node_deep(node)
                    if obj is not None:
                        node_objects[node] = obj
                except Exception:
                    pass

            name_lower = obj_name.lower()
            is_point = ('point' in name_lower) or ('target' in name_lower) or ('aim' in name_lower)
            is_camera = ('camera' in name_lower)
            
            try:
                if beh_viewer.get_behaviour_by_name(obj_id, 'Point') is not None and not beh_viewer.get_behaviour_by_name(obj_id, 'Point').is_null():
                    is_point = True
                if beh_viewer.get_behaviour_by_name(obj_id, 'Camera') is not None and not beh_viewer.get_behaviour_by_name(obj_id, 'Camera').is_null():
                    is_camera = True
            except Exception:
                pass

            target_node_names = []

            if is_point or is_camera:
                target_node_names.extend(['Position', 'Rotation'])
            else:
                target_node_names.extend(['Local Position', 'Local Rotation', 'Local Scale'])
                
            target_node_names.extend([
                'FOV', 'Fov', 'Twist', 'Distance', 'Roll', 'Focal Length',
                'Projected AdditionalVector', 'AdditionalVector',
                'IK Direction', 'LocalDirection', 'Direction'
            ])

            valid_nodes =[]
            for n in target_node_names:
                if n in node_objects:
                    valid_nodes.append((n, node_objects[n]))

            if not valid_nodes:
                fallback_nodes = ['Position', 'Rotation', 'Local Position', 'Local Rotation', 'Local Scale']
                for n in fallback_nodes:
                    if n in node_objects and n not in [v[0] for v in valid_nodes]:
                        valid_nodes.append((n, node_objects[n]))

            if not valid_nodes:
                log(f"  -> SKIP: No valid transform nodes found")
                continue

            # ==========================================================
            # 修正箇所: 値が取得できないノード（アニメーションデータ未保持など）を除外する
            # ==========================================================
            orig_values = {}
            working_valid_nodes = []
            working_actuals = set()
            
            for node_name, obj in valid_nodes:
                try:
                    # 全フレームの値が正常に取得できるかテスト
                    vals = []
                    for frame in frames:
                        vals.append(obj.value(frame))
                    orig_values[node_name] = vals
                    working_valid_nodes.append((node_name, obj))
                    working_actuals.add(obj.data_id())
                except Exception as e:
                    # 取得に失敗したノードはログに残してスキップ
                    log(f"  -> SKIP Node '{node_name}': Data unavailable or does not exist")
                    continue
            
            # エラーが出なかったノードのみに更新
            valid_nodes = working_valid_nodes
            actuals = working_actuals

            if not valid_nodes:
                log(f"  -> SKIP: No readable transform nodes found after testing")
                continue
            # ==========================================================

            log(f"  Target Nodes: {[n for n,_ in valid_nodes]}")

            obj_data.append({
                'obj_id': obj_id,
                'obj_name': obj_name,
                'actuals': actuals,
                'valid_nodes': valid_nodes,
                'orig_values': orig_values,
            })

        log(f"\n--- Writing {len(obj_data)} objects x {len(frames)} frames ---")
        
        total_frames = len(frames)
        all_actuals = set()
        for d in obj_data:
            all_actuals.update(d['actuals'])

        # ==============================================================
        # 補間の事前Fixed化（選択範囲にかかる補間セクションのみを正確に処理する）
        # ==============================================================
        def force_fixed(section):
            section.interval.interpolation = csc.layers.layer.Interpolation.FIXED

        selected_layer_ids = model.layers_selector().all_included_layer_ids()
        
        if len(frames) > 1:
            for layer_id in selected_layer_ids:
                try:
                    layer_obj = lv.layer(layer_id)
                    section_starts = set()
                    
                    # 選択範囲の各フレーム（※終端フレームの直前まで）が所属しているセクションの開始位置を取得
                    # end_frameは補間の結果としての到達点なので、end_frameから始まるセクションは範囲外として除外されます。
                    for frame in range(start_frame, end_frame):
                        try:
                            # 該当フレームが属しているセクションの開始フレーム（キー位置）を取得
                            sec_pos = layer_obj.actual_section_pos(frame)
                            if sec_pos is not None:
                                section_starts.add(sec_pos)
                        except Exception:
                            pass
                            
                    # 割り出した「選択範囲に掛かっているセクションの開始キー」にのみFixedを適用
                    for pos in section_starts:
                        try:
                            le.change_section(pos, layer_id, force_fixed)
                        except Exception:
                            pass
                except Exception as e:
                    log(f"Failed to process layer {layer_id}: {e}")

        for i, frame in enumerate(frames):
            t = easing_table[i]
            src_pos = t * (total_frames - 1)
            
            if total_frames > 1:
                if src_pos < 0.0:
                    src_lo, src_hi = 0, 1
                    frac = src_pos - src_lo
                elif src_pos >= total_frames - 1:
                    src_lo, src_hi = total_frames - 2, total_frames - 1
                    frac = src_pos - src_lo
                else:
                    src_lo = int(src_pos)
                    src_hi = src_lo + 1
                    frac = src_pos - src_lo
            else:
                src_lo = src_hi = 0
                frac = 0.0

            for d in obj_data:
                for node_name, obj in d['valid_nodes']:
                    is_rot = 'Rotation' in node_name
                    val_lo = d['orig_values'][node_name][src_lo]
                    val_hi = d['orig_values'][node_name][src_hi]
                    
                    new_val = interpolate_value(val_lo, val_hi, frac, is_rot=is_rot)
                    
                    # 修正箇所: 値のセット時も念のためエラーを回避
                    try:
                        obj.set_value(new_val, frame)
                    except Exception:
                        pass

            scene_updater.run_update(all_actuals, frame)

        flush_log(gui_dir)
        scene.success(f"Easing Bridge: Bake successfully applied to {len(obj_data)} objects!")

    scene.modify_update_with_session(command_name(), mod)