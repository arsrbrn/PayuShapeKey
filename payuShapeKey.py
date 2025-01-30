import bpy
from bpy.types import Panel, Operator
import mathutils

bl_info = {
    "name": "Shape Key Tools",
    "author": "Claude",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Properties > Data > Shape Keys",
    "description": "シェイプキーの分割・統合・ドライバー設定などの便利な機能をまとめて提供します",
    "warning": "",
    "category": "Mesh",
}

# MMD用の名前マッピング
MMD_NAME_PAIRS = {
    "まばたき": ("ウィンク2", "ｳｨﾝｸ2右"),
    "笑い": ("ウィンク", "ウィンク右"),
}

# 逆引き用の名前マッピング（統合時に使用）
NAME_MAPPING = {
    "ウィンク2": "まばたき",
    "ｳｨﾝｸ2右": "まばたき",
    "ウィンク": "笑い",
    "ウィンク右": "笑い"
}

class ShapeKeyToolsBase:
    """基本的なユーティリティメソッドを提供するベースクラス"""
    
    @classmethod
    def setup_progress(cls, context, total_steps):
        wm = context.window_manager
        wm.progress_begin(0, total_steps)
        
    @classmethod
    def update_progress(cls, context, step):
        wm = context.window_manager
        wm.progress_update(step)
        
    @classmethod
    def end_progress(cls, context):
        wm = context.window_manager
        wm.progress_end()

    @classmethod
    def validate_object(cls, obj):
        """オブジェクトとシェイプキーの妥当性をチェック"""
        if not obj:
            return False, "アクティブオブジェクトが存在しません"
        if obj.type != 'MESH':
            return False, "メッシュオブジェクトではありません"
        if not obj.data.shape_keys:
            return False, "シェイプキーが存在しません"
        return True, ""

    @classmethod
    def get_processable_shape_keys(cls, obj):
        """処理可能なシェイプキーのリストを取得（Basis以外）"""
        if not obj.data.shape_keys:
            return []
        basis = obj.data.shape_keys.reference_key
        return [key for key in obj.data.shape_keys.key_blocks if key != basis]

# [残りのコードはファイルサイズの制限のため分割して続きます]



class MESH_OT_split_shape_key(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.split_shape_key"
    bl_label = "シェイプキー左右分割"
    bl_description = "選択したシェイプキーを左右に分割します"
    bl_options = {'REGISTER', 'UNDO'}

    def store_original_vertices_count(self, obj):
        """元の頂点数を保存（ミラー適用前の左側の頂点数）"""
        return len(obj.data.vertices)

    def store_shape_keys(self, obj):
        """シェイプキーのデータを一時保存する"""
        if not obj.data.shape_keys:
            return None
        
        shape_keys_data = []
        for key_block in obj.data.shape_keys.key_blocks:
            vertex_data = []
            for v in key_block.data:
                vertex_data.append([v.co.x, v.co.y, v.co.z])
            
            shape_keys_data.append({
                'name': key_block.name,
                'value': key_block.value,
                'vertices': vertex_data
            })
        
        return shape_keys_data

    def restore_shape_keys_with_mirror(self, obj, shape_keys_data, original_vertex_count):
        """シェイプキーを復元し、右側にミラーリング"""
        if not shape_keys_data:
            return
        
        # 最初のシェイプキー（Basis）を作成
        basis_data = shape_keys_data[0]
        basis = obj.shape_key_add(name=basis_data['name'])
        
        # 残りのシェイプキーを作成
        for key_data in shape_keys_data[1:]:
            key_block = obj.shape_key_add(name=key_data['name'])
            
            # まず全頂点をBasisの位置にリセット
            for i in range(len(key_block.data)):
                key_block.data[i].co = basis.data[i].co.copy()
            
            # 左側の頂点データを適用（オリジナルの頂点）
            for i in range(original_vertex_count):
                key_block.data[i].co = mathutils.Vector(key_data['vertices'][i])
            
            # 右側の頂点に左側の変形をミラーリング
            current_vertex_count = len(obj.data.vertices)
            for i in range(original_vertex_count):
                left_idx = i
                right_idx = i + original_vertex_count
                
                if right_idx < current_vertex_count:
                    # 左側頂点の変形量を計算
                    left_basis_co = mathutils.Vector(basis_data['vertices'][left_idx])
                    left_shaped_co = mathutils.Vector(key_data['vertices'][left_idx])
                    deform = left_shaped_co - left_basis_co
                    
                    # X座標を反転した変形を右側に適用
                    mirrored_deform = mathutils.Vector((-deform.x, deform.y, deform.z))
                    key_block.data[right_idx].co = basis.data[right_idx].co + mirrored_deform
            
            # シェイプキーの値を設定
            key_block.value = key_data['value']

    def apply_mirror_with_shape_keys(self, context, obj):
        """ミラー修飾子を適用する（シェイプキーを保持）"""
        # 現在の頂点数を保存（ミラー適用前）
        original_vertex_count = self.store_original_vertices_count(obj)
        
        # シェイプキーデータを保存
        shape_keys_data = self.store_shape_keys(obj)
        
        # シェイプキーを一時的に削除
        while obj.data.shape_keys:
            bpy.ops.object.shape_key_remove(all=True)
        
        # ミラー修飾子を適用
        for mod in obj.modifiers:
            if mod.type == 'MIRROR' and mod.show_viewport:
                context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)
        
        # シェイプキーを復元（右側にミラーリング）
        self.restore_shape_keys_with_mirror(obj, shape_keys_data, original_vertex_count)

    def split_shape_key(self, obj, active_key, basis_key):
        """シェイプキーを左右に分割する"""
        # 基準となるシェイプキー名を取得
        base_name = active_key.name.replace("左", "").replace("右", "")
        
        # 元のシェイプキーの値を保存
        original_value = active_key.value
        active_key.value = 1.0
        
        # 左右のシェイプキーを作成
        left_key = obj.shape_key_add(name=f"{base_name}左")
        right_key = obj.shape_key_add(name=f"{base_name}右")
        
        # まず両方のキーに元のシェイプキーの値をコピー
        for i in range(len(basis_key.data)):
            left_key.data[i].co = active_key.data[i].co.copy()
            right_key.data[i].co = active_key.data[i].co.copy()
        
        # X座標を基準に左右を判定して、それぞれの反対側をBasisに戻す
        threshold = 0.001  # 誤差を考慮した閾値
        for i in range(len(basis_key.data)):
            vertex_x = basis_key.data[i].co.x
            if vertex_x > -threshold:  # 右側の頂点（X ≥ 0）
                # 右シェイプキーをBasisに戻す
                right_key.data[i].co = basis_key.data[i].co.copy()
            else:  # 左側の頂点（X < 0）
                # 左シェイプキーをBasisに戻す
                left_key.data[i].co = basis_key.data[i].co.copy()

        # 元のシェイプキーの値を復元
        active_key.value = original_value
        
        # 新規シェイプキーの値を0に設定
        left_key.value = 0.0
        right_key.value = 0.0
        
        return len(obj.data.shape_keys.key_blocks) - 2

    def execute(self, context):
        obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        
        # 現在のモードを保存
        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        try:
            # 最初にミラー修飾子を適用
            for mod in obj.modifiers:
                if mod.type == 'MIRROR' and mod.show_viewport:
                    self.report({'WARNING'}, "ミラー修飾子を適用します...")
                    self.apply_mirror_with_shape_keys(context, obj)
                    self.report({'INFO'}, "ミラー修飾子を適用しました")
                    break
            
            # シェイプキーを取得
            active_key = obj.active_shape_key
            if not active_key:
                self.report({'ERROR'}, "シェイプキーを選択してください")
                return {'CANCELLED'}
            
            basis_key = obj.data.shape_keys.reference_key
            if active_key == basis_key:
                self.report({'ERROR'}, "Basisシェイプキーは分割できません")
                return {'CANCELLED'}
            
            # シェイプキーの分割を実行
            new_index = self.split_shape_key(obj, active_key, basis_key)
            
            # 新しく作成した左のシェイプキーを選択状態にする
            obj.active_shape_key_index = new_index
            
            self.report({'INFO'}, "シェイプキーを左右に分割しました")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"エラーが発生しました: {str(e)}")
            return {'CANCELLED'}
        finally:
            # 元のモードに戻す
            bpy.ops.object.mode_set(mode=original_mode)



class MESH_OT_split_all_shape_keys(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.split_all_shape_keys"
    bl_label = "全シェイプキー左右分割"
    bl_description = "Basis以外の全てのシェイプキーを左右に分割します"
    bl_options = {'REGISTER', 'UNDO'}

    def store_original_vertices_count(self, obj):
        """元の頂点数を保存（ミラー適用前の左側の頂点数）"""
        return len(obj.data.vertices)

    def store_shape_keys(self, obj):
        """シェイプキーのデータを一時保存する"""
        if not obj.data.shape_keys:
            return None
        
        shape_keys_data = []
        for key_block in obj.data.shape_keys.key_blocks:
            vertex_data = []
            for v in key_block.data:
                vertex_data.append([v.co.x, v.co.y, v.co.z])
            
            shape_keys_data.append({
                'name': key_block.name,
                'value': key_block.value,
                'vertices': vertex_data
            })
        
        return shape_keys_data

    def restore_shape_keys_with_mirror(self, obj, shape_keys_data, original_vertex_count):
        """シェイプキーを復元し、右側にミラーリング"""
        if not shape_keys_data:
            return
        
        # 最初のシェイプキー（Basis）を作成
        basis_data = shape_keys_data[0]
        basis = obj.shape_key_add(name=basis_data['name'])
        
        # 残りのシェイプキーを作成
        for key_data in shape_keys_data[1:]:
            key_block = obj.shape_key_add(name=key_data['name'])
            
            # まず全頂点をBasisの位置にリセット
            for i in range(len(key_block.data)):
                key_block.data[i].co = basis.data[i].co.copy()
            
            # 左側の頂点データを適用（オリジナルの頂点）
            for i in range(original_vertex_count):
                key_block.data[i].co = mathutils.Vector(key_data['vertices'][i])
            
            # 右側の頂点に左側の変形をミラーリング
            current_vertex_count = len(obj.data.vertices)
            for i in range(original_vertex_count):
                left_idx = i
                right_idx = i + original_vertex_count
                
                if right_idx < current_vertex_count:
                    # 左側頂点の変形量を計算
                    left_basis_co = mathutils.Vector(basis_data['vertices'][left_idx])
                    left_shaped_co = mathutils.Vector(key_data['vertices'][left_idx])
                    deform = left_shaped_co - left_basis_co
                    
                    # X座標を反転した変形を右側に適用
                    mirrored_deform = mathutils.Vector((-deform.x, deform.y, deform.z))
                    key_block.data[right_idx].co = basis.data[right_idx].co + mirrored_deform
            
            # シェイプキーの値を設定
            key_block.value = key_data['value']

    def apply_mirror_with_shape_keys(self, context, obj):
        """ミラー修飾子を適用する（シェイプキーを保持）"""
        # 現在の頂点数を保存（ミラー適用前）
        original_vertex_count = self.store_original_vertices_count(obj)
        
        # シェイプキーデータを保存
        shape_keys_data = self.store_shape_keys(obj)
        
        # シェイプキーを一時的に削除
        while obj.data.shape_keys:
            bpy.ops.object.shape_key_remove(all=True)
        
        # ミラー修飾子を適用
        for mod in obj.modifiers:
            if mod.type == 'MIRROR' and mod.show_viewport:
                context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)
        
        # シェイプキーを復元（右側にミラーリング）
        self.restore_shape_keys_with_mirror(obj, shape_keys_data, original_vertex_count)

    def split_shape_key(self, obj, active_key, basis_key):
        """シェイプキーを左右に分割する"""
        # まず、このシェイプキー自体が「左」「右」で終わっているかチェック
        if active_key.name.endswith("左") or active_key.name.endswith("右"):
            return False, "既に分割済み"

        # MMDの名前に関連するチェックを先に行う
        for mmd_name, (left_name, right_name) in MMD_NAME_PAIRS.items():
            # ケース1：このシェイプキーがMMDの名前（例：笑い）の場合
            if active_key.name == mmd_name:
                # まず「笑い左」「笑い右」の存在をチェック
                mmd_left = mmd_name + "左"
                mmd_right = mmd_name + "右"
                if mmd_left in obj.data.shape_keys.key_blocks and mmd_right in obj.data.shape_keys.key_blocks:
                    return False, f"既に {mmd_left} と {mmd_right} が存在します"
                
                # 次に「ウィンク」「ウィンク右」の存在をチェック
                if left_name in obj.data.shape_keys.key_blocks and right_name in obj.data.shape_keys.key_blocks:
                    return False, f"既に {left_name} と {right_name} が存在します"
                
                # どちらも存在しない場合は新規作成
                original_value = active_key.value
                left_key = obj.shape_key_add(name=left_name)
                right_key = obj.shape_key_add(name=right_name)
                
                # まず両方のキーに元のシェイプキーの値をコピー
                for i in range(len(basis_key.data)):
                    left_key.data[i].co = active_key.data[i].co.copy()
                    right_key.data[i].co = active_key.data[i].co.copy()
                
                # X座標を基準に左右を判定して、それぞれの反対側をBasisに戻す
                # MMDの場合は左右が反転するので、閾値の判定を逆にする
                threshold = 0.001  # 誤差を考慮した閾値
                for i in range(len(basis_key.data)):
                    vertex_x = basis_key.data[i].co.x
                    if vertex_x >= -threshold:  # 右側の頂点（X ≥ 0）
                        right_key.data[i].co = basis_key.data[i].co.copy()  # MMDでは左側
                    else:  # 左側の頂点（X < 0）
                        left_key.data[i].co = basis_key.data[i].co.copy()  # MMDでは右側
                
                # 値を設定
                left_key.value = 0.0
                right_key.value = 0.0
                
                return True, f"{left_name} と {right_name} を作成しました"
            
            # ケース2：このシェイプキーが「ウィンク」等の場合は分割をスキップ
            elif active_key.name == left_name or active_key.name == right_name:
                return False, "MMD用のシェイプキーは分割できません"
        
        # 通常の左右分割処理
        base_name = active_key.name
        left_exists = f"{base_name}左" in obj.data.shape_keys.key_blocks
        right_exists = f"{base_name}右" in obj.data.shape_keys.key_blocks
        
        if left_exists and right_exists:
            return False, f"既に {base_name}左 と {base_name}右 が存在します"
        
        # 左右のシェイプキーを作成（存在しない場合のみ）
        original_value = active_key.value
        created_keys = []
        
        if not left_exists:
            left_key = obj.shape_key_add(name=f"{base_name}左")
            created_keys.append(f"{base_name}左")
        if not right_exists:
            right_key = obj.shape_key_add(name=f"{base_name}右")
            created_keys.append(f"{base_name}右")
        
        # まず両方にアクティブキーの値をコピー
        for i in range(len(basis_key.data)):
            if not left_exists:
                left_key.data[i].co = active_key.data[i].co.copy()
            if not right_exists:
                right_key.data[i].co = active_key.data[i].co.copy()
        
        # X座標を基準に左右を判定して、それぞれの反対側をBasisに戻す
        threshold = 0.001  # 誤差を考慮した閾値
        for i in range(len(basis_key.data)):
            vertex_x = basis_key.data[i].co.x
            if vertex_x >= -threshold:  # 右側の頂点（X ≥ 0）
                if not right_exists:
                    right_key.data[i].co = basis_key.data[i].co.copy()
            else:  # 左側の頂点（X < 0）
                if not left_exists:
                    left_key.data[i].co = basis_key.data[i].co.copy()

        # 値を設定 - 新規シェイプキーは0に
        if not left_exists:
            left_key.value = 0.0
        if not right_exists:
            right_key.value = 0.0
        
        if created_keys:
            return True, f"{' と '.join(created_keys)} を作成しました"
        return False, "作成するシェイプキーがありません"

    def execute(self, context):
        obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        # 現在のモードを保存
        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        try:
            # 最初にミラー修飾子を適用
            for mod in obj.modifiers:
                if mod.type == 'MIRROR' and mod.show_viewport:
                    self.report({'WARNING'}, "ミラー修飾子を適用します...")
                    self.apply_mirror_with_shape_keys(context, obj)
                    self.report({'INFO'}, "ミラー修飾子を適用しました")
                    break

            # 処理可能なシェイプキーを取得
            basis_key = obj.data.shape_keys.reference_key
            shape_keys = [key for key in obj.data.shape_keys.key_blocks if key != basis_key]
            
            if not shape_keys:
                self.report({'WARNING'}, "処理可能なシェイプキーが見つかりません")
                return {'CANCELLED'}

            # プログレスバーを初期化
            self.setup_progress(context, len(shape_keys))
            
            success_count = 0
            skipped_count = 0
            messages = []

            # 各シェイプキーを処理
            for i, key in enumerate(shape_keys):
                try:
                    result, message = self.split_shape_key(obj, key, basis_key)
                    if result:
                        success_count += 1
                    else:
                        if "既に" in message or "作成するシェイプキーがありません" in message:
                            skipped_count += 1
                        if message not in messages:  # 重複するメッセージを避ける
                            messages.append(message)
                except Exception as e:
                    print(f"Error processing shape key {key.name}: {str(e)}")
                    messages.append(f"{key.name} の処理中にエラーが発生しました")

                self.update_progress(context, i + 1)

            # 結果を報告
            if success_count > 0:
                message = f"{success_count}個のシェイプキーを分割しました"
                if skipped_count > 0:
                    message += f" ({skipped_count}個をスキップ)"
                self.report({'INFO'}, message)
                # 詳細なメッセージをコンソールに出力
                for msg in messages:
                    print(msg)
                return {'FINISHED'}
            else:
                if skipped_count > 0:
                    self.report({'INFO'}, f"全ての{skipped_count}個のシェイプキーが既に処理済みです")
                else:
                    self.report({'WARNING'}, "分割可能なシェイプキーが見つかりませんでした")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"エラーが発生しました: {str(e)}")
            return {'CANCELLED'}
        finally:
            # プログレスバーを終了
            self.end_progress(context)
            # 元のモードに戻す
            bpy.ops.object.mode_set(mode=original_mode)




class MESH_OT_merge_shape_key(Operator):
    bl_idname = "mesh.merge_shape_key"
    bl_label = "シェイプキー左右統合"
    bl_description = "選択したシェイプキーの左右を統合します"
    bl_options = {'REGISTER', 'UNDO'}

    def find_matching_shape_keys(self, obj, active_key):
        """選択されたシェイプキーに対応する左右のシェイプキーを見つける"""
        if not active_key or not active_key.name:
            return None, None, None

        active_name = active_key.name
        
        # MMDパターンをチェック
        for mmd_name, (left_name, right_name) in MMD_NAME_PAIRS.items():
            # 左側が選択された場合
            if active_name == left_name:
                # 右側を探す
                right_key = obj.data.shape_keys.key_blocks.get(right_name)
                if right_key:
                    return active_key, right_key, mmd_name
            # 右側が選択された場合
            elif active_name == right_name:
                # 左側を探す
                left_key = obj.data.shape_keys.key_blocks.get(left_name)
                if left_key:
                    return left_key, active_key, mmd_name

        # 通常パターンをチェック（「左」「右」で終わる名前）
        if active_name.endswith("左"):
            base_name = active_name[:-1]
            right_key = obj.data.shape_keys.key_blocks.get(base_name + "右")
            if right_key:
                return active_key, right_key, base_name
        elif active_name.endswith("右"):
            base_name = active_name[:-1]
            left_key = obj.data.shape_keys.key_blocks.get(base_name + "左")
            if left_key:
                return left_key, active_key, base_name

        return None, None, None

    def merge_shape_keys(self, obj, left_key, right_key, merged_name):
        """左右のシェイプキーを統合"""
        if not (left_key and right_key):
            return None
        
        # 元のシェイプキーの値を保存
        original_value = left_key.value
        
        # 同名のシェイプキーが既に存在するかチェック
        existing_key = obj.data.shape_keys.key_blocks.get(merged_name)
        
        # 同名のシェイプキーが存在する場合
        if existing_key:
            # 左右のシェイプキーを削除
            obj.shape_key_remove(right_key)
            obj.shape_key_remove(left_key)
            return existing_key
        
        # 新しいシェイプキーを作成
        merged_key = obj.shape_key_add(name=merged_name, from_mix=False)
        
        # X座標を基準に左右を判定
        threshold = 0.001  # 誤差を考慮した閾値
        basis_key = obj.data.shape_keys.reference_key
        
        # 頂点ごとに処理
        for i in range(len(merged_key.data)):
            vertex_x = basis_key.data[i].co.x
            if vertex_x > -threshold:  # 右側の頂点（X ≥ 0）
                merged_key.data[i].co = right_key.data[i].co.copy()
            else:  # 左側の頂点（X < 0）
                merged_key.data[i].co = left_key.data[i].co.copy()
        
        # 値を設定
        merged_key.value = original_value
        
        # 元のシェイプキーを削除
        obj.shape_key_remove(right_key)
        obj.shape_key_remove(left_key)
        
        return merged_key

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data.shape_keys:
            self.report({'ERROR'}, "シェイプキーが存在しません")
            return {'CANCELLED'}
        
        active_key = obj.active_shape_key
        if not active_key:
            self.report({'ERROR'}, "シェイプキーを選択してください")
            return {'CANCELLED'}
        
        # 左右のシェイプキーを見つける
        left_key, right_key, merged_name = self.find_matching_shape_keys(obj, active_key)
        
        if not (left_key and right_key):
            self.report({'ERROR'}, "対応する左右のシェイプキーが見つかりません")
            return {'CANCELLED'}
        
        # シェイプキーを統合
        merged_key = self.merge_shape_keys(obj, left_key, right_key, merged_name)
        
        if not merged_key:
            self.report({'ERROR'}, "シェイプキーの統合に失敗しました")
            return {'CANCELLED'}
        
        # 統合したシェイプキーを選択
        obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks).index(merged_key)
        
        self.report({'INFO'}, f"シェイプキーを '{merged_name}' として統合しました")
        return {'FINISHED'}




class MESH_OT_merge_all_shape_keys(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.merge_all_shape_keys"
    bl_label = "全シェイプキー左右統合"
    bl_description = "全ての左右シェイプキーを統合します"
    bl_options = {'REGISTER', 'UNDO'}

    def get_shape_key_pairs(self, obj):
        """統合可能な左右のシェイプキーペアを収集"""
        pairs = []
        processed = set()
        basis = obj.data.shape_keys.reference_key

        # すべてのシェイプキーをチェック
        for key in obj.data.shape_keys.key_blocks:
            if key == basis or key.name in processed:
                continue

            # MMDパターンをチェック
            # MMD_NAME_PAIRSの値をタプルとして取得
            for mmd_name, (left_name, right_name) in MMD_NAME_PAIRS.items():
                if key.name == left_name:
                    right_key = obj.data.shape_keys.key_blocks.get(right_name)
                    if right_key:
                        pairs.append((key, right_key, mmd_name))
                        processed.add(left_name)
                        processed.add(right_name)
                        break
                elif key.name == right_name:
                    left_key = obj.data.shape_keys.key_blocks.get(left_name)
                    if left_key:
                        pairs.append((left_key, key, mmd_name))
                        processed.add(left_name)
                        processed.add(right_name)
                        break

            # 通常パターンをチェック
            if key.name.endswith("左"):
                base_name = key.name[:-1]
                right_key = obj.data.shape_keys.key_blocks.get(base_name + "右")
                if right_key:
                    pairs.append((key, right_key, base_name))
                    processed.add(key.name)
                    processed.add(right_key.name)
            elif key.name.endswith("右") and key.name not in processed:
                base_name = key.name[:-1]
                left_key = obj.data.shape_keys.key_blocks.get(base_name + "左")
                if left_key:
                    pairs.append((left_key, key, base_name))
                    processed.add(left_key.name)
                    processed.add(key.name)

        return pairs

    def merge_single_pair(self, obj, left_key, right_key, merged_name):
        """1組のシェイプキーを安全に統合"""
        if not all([left_key, right_key]):
            return False

        try:
            # 既存のシェイプキーをチェック
            existing_key = obj.data.shape_keys.key_blocks.get(merged_name)
            if existing_key:
                # 既存のキーを保持し、左右のキーを個別に削除
                if left_key.name in obj.data.shape_keys.key_blocks:
                    obj.shape_key_remove(left_key)
                if right_key.name in obj.data.shape_keys.key_blocks:
                    obj.shape_key_remove(right_key)
                return True

            # 新しいキーを作成
            original_value = left_key.value
            new_key = obj.shape_key_add(name=merged_name, from_mix=False)
            basis_key = obj.data.shape_keys.reference_key

            # 頂点データをコピー
            for i, data in enumerate(new_key.data):
                if basis_key.data[i].co.x > -0.001:  # 右側
                    data.co = right_key.data[i].co.copy()
                else:  # 左側
                    data.co = left_key.data[i].co.copy()

            # 値を設定
            new_key.value = original_value

            # 古いキーを個別に削除
            if right_key.name in obj.data.shape_keys.key_blocks:
                obj.shape_key_remove(right_key)
            if left_key.name in obj.data.shape_keys.key_blocks:
                obj.shape_key_remove(left_key)

            return True

        except Exception as e:
            print(f"Error merging pair {left_key.name}/{right_key.name}: {str(e)}")
            return False

    def execute(self, context):
        obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        # 統合可能なペアを収集
        pairs = self.get_shape_key_pairs(obj)
        if not pairs:
            self.report({'WARNING'}, "統合可能なシェイプキーが見つかりません")
            return {'CANCELLED'}

        # プログレスバーを初期化
        self.setup_progress(context, len(pairs))
        
        try:
            success_count = 0
            error_count = 0

            # 各ペアを処理
            for i, (left_key, right_key, merged_name) in enumerate(pairs):
                try:
                    if self.merge_single_pair(obj, left_key, right_key, merged_name):
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    print(f"Error processing pair: {str(e)}")
                    error_count += 1

                self.update_progress(context, i + 1)

            # 結果を報告
            if success_count > 0:
                message = f"{success_count}組のシェイプキーを統合しました"
                if error_count > 0:
                    message += f" ({error_count}個の処理に失敗)"
                self.report({'INFO'}, message)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "シェイプキーの統合に失敗しました")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"エラーが発生しました: {str(e)}")
            return {'CANCELLED'}
        finally:
            self.end_progress(context)            
            
            
class MESH_OT_rename_shape_keys_for_mmd(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.rename_shape_keys_for_mmd"
    bl_label = "シェイプキー名をMMD用に変更"
    bl_description = "シェイプキーの名前をMMD用に変更します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        renamed_count = 0
        # 全てのシェイプキーをチェック
        for key_block in obj.data.shape_keys.key_blocks:
            # まず通常の左右シェイプキーをチェック
            if key_block.name.endswith("左") or key_block.name.endswith("右"):
                base_name = key_block.name[:-1]  # "左"または"右"を除いた名前
                
                # MMDペアの中から対応する名前を探す
                for mmd_name, (left_name, right_name) in MMD_NAME_PAIRS.items():
                    if base_name == mmd_name:
                        # 左右に応じて適切な名前を設定
                        if key_block.name.endswith("左"):
                            key_block.name = left_name
                        else:
                            key_block.name = right_name
                        renamed_count += 1
                        break

        if renamed_count > 0:
            self.report({'INFO'}, f"{renamed_count}個のシェイプキーの名前を変更しました")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "変更対象のシェイプキーが見つかりませんでした")
            return {'CANCELLED'}
                

class MESH_OT_add_shape_key_drivers(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.add_shape_key_drivers"
    bl_label = "シェイプキードライバー追加"
    bl_description = "選択シェイプキーと同名のシェイプキーをアクティブオブジェクトに連動させます"
    bl_options = {'REGISTER', 'UNDO'}

    def add_driver(self, source_obj, source_key, target_obj, target_key):
        """ドライバーを追加する"""
        # 既存のドライバーを削除
        if target_key.driver_remove("value"):
            print(f"Removed existing driver from {target_obj.name}.{target_key.name}")
        
        # 新しいドライバーを追加
        driver = target_key.driver_add("value")
        if not driver:
            return False
            
        # ドライバーの設定
        driver = driver.driver
        driver.type = 'AVERAGE'
        
        # 変数を追加
        var = driver.variables.new()
        var.name = "var"
        var.type = 'SINGLE_PROP'
        
        # ターゲットの設定
        target = var.targets[0]
        target.id_type = 'MESH'
        target.id = source_obj.data
        target.data_path = f'shape_keys.key_blocks["{source_key.name}"].value'
        
        return True

    def execute(self, context):
        source_obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(source_obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        active_key = source_obj.active_shape_key
        if not active_key:
            self.report({'ERROR'}, "シェイプキーを選択してください")
            return {'CANCELLED'}

        if active_key == source_obj.data.shape_keys.reference_key:
            self.report({'ERROR'}, "Basisシェイプキーには設定できません")
            return {'CANCELLED'}

        # シーン内の全メッシュオブジェクトを取得（アクティブを除く）
        target_objects = [obj for obj in bpy.data.objects 
                         if obj != source_obj and obj.type == 'MESH' and obj.data.shape_keys]

        if not target_objects:
            self.report({'WARNING'}, "他にシェイプキーを持つオブジェクトが見つかりません")
            return {'CANCELLED'}

        # プログレスバーを初期化
        self.setup_progress(context, len(target_objects))

        try:
            driver_count = 0
            error_count = 0
            
            # 各オブジェクトに対して処理
            for i, obj in enumerate(target_objects):
                if obj.data.shape_keys and active_key.name in obj.data.shape_keys.key_blocks:
                    target_key = obj.data.shape_keys.key_blocks[active_key.name]
                    if self.add_driver(source_obj, active_key, obj, target_key):
                        driver_count += 1
                    else:
                        error_count += 1
                
                # プログレスバーを更新
                self.update_progress(context, i + 1)

            if driver_count > 0:
                message = f"{driver_count}個のドライバーを設定しました"
                if error_count > 0:
                    message += f" ({error_count}個の設定に失敗)"
                self.report({'INFO'}, message)
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "設定可能なドライバーが見つかりませんでした")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"エラーが発生しました: {str(e)}")
            return {'CANCELLED'}
        finally:
            # プログレスバーを終了
            self.end_progress(context)





class MESH_OT_add_all_shape_key_drivers(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.add_all_shape_key_drivers"
    bl_label = "全シェイプキーにドライバー追加"
    bl_description = "全シェイプキーに対してドライバーを設定します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source_obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(source_obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        # 処理可能なシェイプキーを取得
        shape_keys = self.get_processable_shape_keys(source_obj)
        if not shape_keys:
            self.report({'WARNING'}, "処理可能なシェイプキーが見つかりません")
            return {'CANCELLED'}

        # シーン内の対象オブジェクトを取得
        target_objects = [obj for obj in bpy.data.objects 
                         if obj != source_obj and obj.type == 'MESH' and obj.data.shape_keys]

        if not target_objects:
            self.report({'WARNING'}, "他にシェイプキーを持つオブジェクトが見つかりません")
            return {'CANCELLED'}

        # プログレスバーを初期化
        total_steps = len(shape_keys)
        self.setup_progress(context, total_steps)

        try:
            success_count = 0
            error_count = 0
            shape_key_count = 0
            
            # 各シェイプキーを処理
            for i, key in enumerate(shape_keys):
                try:
                    # 現在のシェイプキーを選択
                    source_obj.active_shape_key_index = list(source_obj.data.shape_keys.key_blocks).index(key)
                    
                    # 各対象オブジェクトに対してドライバーを設定
                    for target_obj in target_objects:
                        if key.name in target_obj.data.shape_keys.key_blocks:
                            target_key = target_obj.data.shape_keys.key_blocks[key.name]
                            
                            # 既存のドライバーを削除
                            if target_key.driver_remove("value"):
                                print(f"Removed existing driver from {target_obj.name}.{key.name}")
                            
                            # 新しいドライバーを追加
                            driver = target_key.driver_add("value")
                            if driver:
                                driver = driver.driver
                                driver.type = 'AVERAGE'
                                
                                # 変数を追加
                                var = driver.variables.new()
                                var.name = "var"
                                var.type = 'SINGLE_PROP'
                                
                                # ターゲットの設定
                                target = var.targets[0]
                                target.id_type = 'MESH'
                                target.id = source_obj.data
                                target.data_path = f'shape_keys.key_blocks["{key.name}"].value'
                                
                                shape_key_count += 1
                                success_count += 1
                            else:
                                error_count += 1
                    
                except Exception as e:
                    print(f"Error processing shape key {key.name}: {str(e)}")
                    error_count += 1
                
                # プログレスバーを更新
                self.update_progress(context, i + 1)

            # 結果を報告
            if success_count > 0:
                message = f"{success_count}個のドライバーを設定しました（{shape_key_count}個のシェイプキー）"
                if error_count > 0:
                    message += f"\n{error_count}個の設定に失敗しました"
                self.report({'INFO'}, message)
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "ドライバーを設定できませんでした")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"エラーが発生しました: {str(e)}")
            return {'CANCELLED'}
        finally:
            # プログレスバーを終了
            self.end_progress(context)
            
            
            
            
            
class MESH_OT_remove_shape_key_drivers(Operator, ShapeKeyToolsBase):
    bl_idname = "mesh.remove_shape_key_drivers"
    bl_label = "シェイプキードライバー削除"
    bl_description = "選択シェイプキーと同名のシェイプキードライバーを削除します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source_obj = context.active_object
        
        # オブジェクトの妥当性チェック
        valid, message = self.validate_object(source_obj)
        if not valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        active_key = source_obj.active_shape_key
        if not active_key:
            self.report({'ERROR'}, "シェイプキーを選択してください")
            return {'CANCELLED'}

        # 他の全メッシュオブジェクトを処理
        removed_count = 0
        affected_objects = []
        
        for obj in bpy.data.objects:
            if obj != source_obj and obj.type == 'MESH' and obj.data.shape_keys:
                if active_key.name in obj.data.shape_keys.key_blocks:
                    shape_key = obj.data.shape_keys.key_blocks[active_key.name]
                    if shape_key.driver_remove("value"):
                        removed_count += 1
                        affected_objects.append(obj)
                        
                        # シェイプキーの値を0にリセット
                        shape_key.value = 0.0

        # 更新を強制
        if affected_objects:
            # 各オブジェクトの更新を強制
            for obj in affected_objects:
                # オブジェクトに変更があったことを通知
                obj.update_tag()
                
                # メッシュデータに変更があったことを通知
                if obj.data:
                    obj.data.update()
            
            # シーンの更新を強制
            context.view_layer.update()

        if removed_count > 0:
            self.report({'INFO'}, f"{removed_count}個のドライバーを削除しました")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "削除できるドライバーが見つかりませんでした")
            return {'CANCELLED'}          



class MESH_PT_shape_key_tools_main(Panel):
    bl_label = "Payu Shape Key"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_order = 9  # シェイプキーパネル（10）の直前に配置

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='SOLO_ON')  # 星アイコン

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        obj = context.object

        if not obj.data.shape_keys:
            # シェイプキーがない場合は作成ボタンを表示
            row = layout.row()
            row.operator("object.shape_key_add", icon='ADD', text="Add Shape Key")
            return

        # ドライバーツール（独立したグループ）
        col = layout.column(align=False)  # align=False で要素間に適度な間隔を確保
        
        row = col.row(align=True)
        split = row.split(factor=0.85, align=True)
        split.operator("mesh.add_shape_key_drivers", text="ドライバーを追加", icon='DRIVER')
        split.operator("mesh.remove_shape_key_drivers", text="", icon='X')
        
        # 分割線を追加してグループを明確に分ける
        col.separator(factor=0.5)
        
        # 分割/統合ツール（独立したグループ）
        row = col.row(align=True)
        split = row.split(factor=0.5, align=True)
        split.operator("mesh.split_shape_key", text="Split", icon='MOD_MIRROR')
        split.operator("mesh.merge_shape_key", text="Merge", icon='AUTOMERGE_ON')
        



def shape_key_specials_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("mesh.split_all_shape_keys", text="全シェイプキーを左右分割", icon='MOD_MIRROR')
    layout.operator("mesh.merge_all_shape_keys", text="全シェイプキーを左右統合")
    layout.separator()  # 区切り線を追加
    layout.operator("mesh.rename_shape_keys_for_mmd", text="シェイプキー名をMMD用に変更", icon='SORTALPHA')
    layout.separator()  # 区切り線を追加
    layout.operator("mesh.add_all_shape_key_drivers", text="全シェイプキーにドライバー追加", icon='DRIVER')

def register():
    bpy.utils.register_class(MESH_OT_split_shape_key)
    bpy.utils.register_class(MESH_OT_split_all_shape_keys)
    bpy.utils.register_class(MESH_OT_merge_shape_key)
    bpy.utils.register_class(MESH_OT_merge_all_shape_keys)
    bpy.utils.register_class(MESH_OT_add_shape_key_drivers)
    bpy.utils.register_class(MESH_OT_add_all_shape_key_drivers)
    bpy.utils.register_class(MESH_OT_remove_shape_key_drivers)
    bpy.utils.register_class(MESH_OT_rename_shape_keys_for_mmd)
    bpy.utils.register_class(MESH_PT_shape_key_tools_main)
    bpy.types.MESH_MT_shape_key_context_menu.append(shape_key_specials_menu)

def unregister():
    bpy.types.MESH_MT_shape_key_context_menu.remove(shape_key_specials_menu)
    bpy.utils.unregister_class(MESH_PT_shape_key_tools_main)
    bpy.utils.unregister_class(MESH_OT_rename_shape_keys_for_mmd)
    bpy.utils.unregister_class(MESH_OT_remove_shape_key_drivers)
    bpy.utils.unregister_class(MESH_OT_add_all_shape_key_drivers)
    bpy.utils.unregister_class(MESH_OT_add_shape_key_drivers)
    bpy.utils.unregister_class(MESH_OT_merge_all_shape_keys)
    bpy.utils.unregister_class(MESH_OT_merge_shape_key)
    bpy.utils.unregister_class(MESH_OT_split_all_shape_keys)
    bpy.utils.unregister_class(MESH_OT_split_shape_key)

if __name__ == "__main__":
    register()