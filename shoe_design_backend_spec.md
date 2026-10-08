# Shoe Design Workflow Backend — Project Specification

> **Source of truth** cho backend hiện tại: **Django + DRF + PostgreSQL**, triển khai dạng **microservices** trong thư mục `paihong_apis/`.
>
> Tài liệu này phản ánh **đúng source code đang chạy**, không phải thiết kế cũ.

---

## 1. Mục tiêu hệ thống

Backend quản lý quy trình thiết kế giày:

1. Một **WorkItem** (design) có **một** `item_code` **duy nhất**, gắn **workflow template**, và **một hoặc nhiều file gốc** (`SourceDocument`).
2. Mỗi file gốc được convert/detect thành **0..N Part** (mỗi SVG/page = 1 Part).
3. Mỗi Part đi qua **workflow nhiều bước** (`PartStep`), định nghĩa bởi master data `WorkflowStepDefinition` + `WorkflowTemplate`.
4. Mỗi bước có lịch sử **StepRevision** (autosave / manual / official / restore), settings JSON riêng, và **0..N file output** (`RevisionArtifact` → `FileObject`).
5. File binary **không lưu trong PostgreSQL** — chỉ metadata; vật lý nằm local/NAS/MinIO/S3.
6. Dùng **SHA256 + deduplicate** để tránh ghi đè nội dung file.

---



## 2. Kiến trúc triển khai



### 2.1 Microservices


| Service              | Port host             | Mô tả                                       |
| -------------------- | --------------------- | ------------------------------------------- |
| `user_service`       | **9001**              | Auth, User CRUD                             |
| `design_service`     | **9002**              | WorkItem, SourceDocument, Part, Workflow    |
| `revision_service`   | **9003**              | PartStep, StepRevision                      |
| `nginx`              | `${FORWARD_PORT:-82}` | Reverse proxy + serve `/media/`, `/static/` |
| `db` (PostgreSQL 16) | 5434                  | Database chung                              |
| `redis`              | 6379                  | Cache / Celery broker                       |


Code dùng chung: `paihong_apis/app/`, `paihong_apis/core/`. Mỗi service mount `services/{user,design,revision}/apis/` và `.env` riêng.

### 2.2 Nginx routing


| Pattern                                                                         | Upstream         |
| ------------------------------------------------------------------------------- | ---------------- |
| `/api/v1/(auth|users)`                                                          | user_service     |
| `/api/v1/parts/{id}/steps/...`, `/sync-steps`                                   | revision_service |
| `/api/v1/revisions/...`                                                         | revision_service |
| `/api/v1/(work-items|source-documents|workflow-templates|workflow-steps|parts)` | design_service   |
| `/media/`, `/static/`                                                           | shared volumes   |


**Lưu ý quan trọng:** Django đăng ký URL với **underscore** (`work_items`, `source_documents`). Nginx regex dùng **hyphen** (`work-items`). Khi gọi trực tiếp service port (9001/9002/9003) dùng underscore. Qua nginx port 82 cần đảm bảo path khớp hoặc sửa nginx.

### 2.3 Response envelope

Mọi API business trả về:

```json
{
  "status": true,
  "data": { ... },
  "message": "..."
}
```

Lỗi validation: `{ "status": false, "message": "..." }` (400).  
Revision conflict: **409** (`base_revision_id` không khớp `latest_revision`).  
Auth: **401**, Not found: **404**.

---



## 3. Sơ đồ dữ liệu

```text
User (soft delete)
 │
 ├── WorkItem ──N──► SourceDocument ──N──► Part
 │                      │                  │
 │                      │                  ├── PartStep ──N──► StepRevision ──N──► RevisionArtifact
 │                      │                  │         │
 │                      ▼                  │         └──► WorkflowStepDefinition
 │                 FileObject ◄────────────┴── preview_file / artifacts / source file
 │
WorkflowTemplate ──N──► TemplateStep ──► WorkflowStepDefinition

PartStep (START_DESIGNING) ──1──► DesignWorkspace ──N──► DesignFile ──N──► DesignFileRevision ──► FileObject (snapshot/tiles)
ColorDefinition ◄── UserColorPreference ──► User
```

**Quy ước quan hệ:**

- `WorkItem 1:N SourceDocument` — không lưu file trực tiếp trên WorkItem.
- `SourceDocument 1:N Part` — Part **không có FK** `work_item_id`; suy ra qua `part.source_document.work_item` (property trên model).
- `Part 1:N PartStep` — mỗi cặp `(part, step)` duy nhất.
- `PartStep 1:N StepRevision` — revision immutable ở tầng nghiệp vụ.
- `StepRevision 1:N RevisionArtifact`.

---



## 4. Enums (IntegerChoices)

Tất cả enum lưu **integer** trong DB/API (không phải string).


| Enum                         | Giá trị                                                     |
| ---------------------------- | ----------------------------------------------------------- |
| **UserRoleEnum**             | 1=Developer, 2=Admin, 3=Customer, 4=Designer                |
| **UserStatusEnum**           | 1=Active, 2=Inactive, 3=Suspended                           |
| **StorageBackendEnum**       | 1=Local, 2=NAS, 3=MinIO, 4=S3                               |
| **WorkItemStatusEnum**       | 1=New, 2=Pre-processing, 3=Designing, 4=Completed, 5=Failed |
| **SourceDocumentStatusEnum** | 1=Uploaded, 2=Processing, 3=Processed, 4=Failed             |
| **PartStatusEnum**           | 1=New, 2=Processing, 3=Completed, 4=Failed                  |
| **StepStatusEnum**           | 1=Not started, 2=In progress, 3=Done                        |
| **RevisionTypeEnum**         | 1=Autosave, 2=Manual, 3=Official, 4=Restore                 |


**Hằng số nghiệp vụ** (`core/constant.py`):

- `BOOTSTRAP_DONE_STEP_CODES = ("RECEIVE_FILES")` — auto-complete bước 1 khi tạo Part.
- `WORKFLOW_ACTIVE_START_STEP_CODE = "PICK_UPPER"` — bước 2, bước đầu user làm thủ công.
- `AUTOSAVE_KEEP_LATEST = 12`
- `ALLOWED_SOURCE_EXTENSIONS = ["pdf", "ai", "dxf"]` (max 50 MB/file)
- `ALLOWED_ARTIFACT_EXTENSIONS = ["png","jpg","jpeg","json","svg","dxf","pdf"]`
- `DEFAULT_OUTPUT_ARTIFACT_ROLE = "OUTPUT_IMAGE"`

**10 workflow steps** (`WORKFLOW_STEP_SEED`):


| Seq | Code                 | Name                   |
| --- | -------------------- | ---------------------- |
| 1   | RECEIVE_FILES        | Receive files          |
| 2   | PICK_UPPER           | Pick the upper         |
| 3   | ROTATE_STRIP_TEXT    | Rotate · strip text    |
| 4   | REMOVE_AUX_LINES     | Remove aux lines       |
| 5   | FIX_LINES_BY_ANCHOR  | Fix lines by anchor    |
| 6   | CHECK_COLORS         | Check colors           |
| 7   | CANVAS_FRAME_MEASURE | Canvas frame · measure |
| 8   | ENTER_SPECS          | Enter specs            |
| 9   | BUILD_GRID           | Build grid             |
| 10  | START_DESIGNING      | Start designing        |


Seed: `python manage.py seed_workflow_steps` → template mặc định `STANDARD_SHOE`.

---



## 5. Models

Tất cả model nghiệp vụ (trừ User) dùng `TimeStampedModel` → fields `created`, `modified` (không phải `created_at`/`updated_at`).

**Chỉ** `User` **dùng soft delete** (`django_softdelete`).

### 5.1 User (`users`)


| Field            | Ghi chú                       |
| ---------------- | ----------------------------- |
| `id`             | UUID PK                       |
| `username`       | unique                        |
| `role`, `status` | int, indexed                  |
| `avatar`         | FK → FileObject, nullable     |
| `token_version`  | UUID — invalidate JWT khi đổi |




### 5.2 FileObject (`file_object`)


| Field                                | Ghi chú                                                  |
| ------------------------------------ | -------------------------------------------------------- |
| `storage_backend`                    | int                                                      |
| `storage_key`                        | **unique**, format `objects/{sha256[:2]}/{sha256}.{ext}` |
| `sha256`, `size_bytes`               | dedup index                                              |
| `extension`, `mime_type`, `metadata` |                                                          |


URL public: `{BE_DOMAIN}{MEDIA_URL}{storage_key}` (xem §12).

### 5.3 WorkItem (`work_item`)


| Field                      | Ghi chú                        |
| -------------------------- | ------------------------------ |
| `item_code`                | **unique** (migration `0003`)  |
| `name`, `status`           |                                |
| `workflow_template`        | FK → WorkflowTemplate, PROTECT |
| `created_by`, `updated_by` | FK → User                      |


Index: `(status, -created)`.

### 5.4 SourceDocument (`source_document`)


| Field                                                      | Ghi chú                 |
| ---------------------------------------------------------- | ----------------------- |
| `work_item`                                                | FK CASCADE              |
| `file`                                                     | FK PROTECT → FileObject |
| `sequence`                                                 | unique per work_item    |
| `original_filename`, `document_type`, `status`, `metadata` |                         |




### 5.5 Part (`part`)


| Field                                             | Ghi chú                       |
| ------------------------------------------------- | ----------------------------- |
| `source_document`                                 | FK CASCADE                    |
| `sequence`                                        | unique per source_document    |
| `name`, `status`                                  |                               |
| `source_page`, `source_bbox`, `detected_metadata` |                               |
| `preview_file`                                    | FK → FileObject (SVG preview) |


Property: `work_item` → `source_document.work_item`.

### 5.6 WorkflowStepDefinition (`workflow_step_definition`)


| Field                                         | Ghi chú                      |
| --------------------------------------------- | ---------------------------- |
| `id`                                          | SmallAutoField PK            |
| `code`                                        | unique                       |
| `sequence`                                    | unique                       |
| `name`, `description`, `version`, `is_active` |                              |
| `settings_schema_key`                         | map tới validator serializer |




### 5.7 WorkflowTemplate + TemplateStep

- `WorkflowTemplate`: `code` unique, `is_default`, `is_active`.
- `TemplateStep`: unique `(template, step)` và `(template, sequence)`.



### 5.8 PartStep (`part_step`)


| Field                                  | Ghi chú                     |
| -------------------------------------- | --------------------------- |
| `part`, `step`                         | unique together             |
| `status`                               | StepStatusEnum              |
| `started_at`, `completed_at`           |                             |
| `latest_revision`, `official_revision` | FK → StepRevision, SET_NULL |




### 5.9 StepRevision (`step_revision`)


| Field                                                             | Ghi chú                    |
| ----------------------------------------------------------------- | -------------------------- |
| `part_step`, `revision_no`                                        | unique together, monotonic |
| `revision_type`                                                   | RevisionTypeEnum           |
| `parent_revision`                                                 | self-FK (restore chain)    |
| `settings`                                                        | JSON                       |
| `settings_schema_version`, `app_version`, `settings_hash`, `note` |                            |


**Immutable** ở service layer — không có API xóa revision trực tiếp.

### 5.10 RevisionArtifact (`revision_artifact`)


| Field                  | Ghi chú                             |
| ---------------------- | ----------------------------------- |
| `revision`, `file`     |                                     |
| `role`, `sequence`     | unique `(revision, role, sequence)` |
| `filename`, `metadata` |                                     |




### 5.11 DesignWorkspace / DesignFile / DesignFileRevision (step 10)


| Model                | Ghi chú                                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DesignWorkspace`    | 1:1 `PartStep` (START_DESIGNING); `settings` JSON nhẹ (active_file_type, progress)                                                                |
| `DesignFile`         | unique `(workspace, file_type)`; 8 slots: `S,S1,C,H,P,F,FC,KMO`; `display_name` = `{item_code}_*.png` / `{item_code}.kmo`                         |
| `DesignFileRevision` | immutable revisions; `layers[]`, `grid_width/height` (kích thước grid **của revision này**, đổi được qua PATCH tiles), `snapshot_file` → FileObject (gzip JSON tile map), `preview_file` → PNG thumbnail (autosave/save/PATCH tiles/complete giữ preview cũ); `tile_manifest` nội bộ BE, không expose API |


Grid body **không** lưu trong PostgreSQL rows — snapshot + tile blobs trên object storage (`GRID_TILE_SIZE=64`, schema v2).

### 5.12 ColorDefinition / UserColorPreference


| Model                 | Ghi chú                                                                   |
| --------------------- | ------------------------------------------------------------------------- |
| `ColorDefinition`     | System palette: `code`, `hex_value`, `name`, `display_order`, `is_system`. Chỉ **Admin/Developer** được thêm/sửa/xóa qua `/system_colors`; user khác chỉ load |
| `UserColorPreference` | Chỉ màu **custom** của user: `code`, `custom_hex`, `custom_name`, `display_order`. Không còn override màu system (đã bỏ FK `color_definition`, migration `0008`) |

Cả 2 model dùng chung tên field sắp xếp `display_order` (migration `0009` đổi `ColorDefinition.default_order` → `display_order`).

**Rule màu system:** `code` unique trong system (constraint DB), `hex_value` chuẩn hóa `#RRGGBB` và không trùng hex system khác (không phân biệt hoa/thường), `name` bắt buộc. Thêm/sửa màu system **không** kiểm tra trùng với màu custom đã có của user.

**Rule màu custom** (enforce ở serializer + DB):

- `code` bắt buộc, integer ≥ 1, **unique trong các màu custom của chính user** (constraint DB `uq_user_color_code` trên `(user, code)`). Được trùng `code` của màu system và của user khác.
- `hex_value` bắt buộc, chuẩn hóa `#RRGGBB`, **không trùng** (không phân biệt hoa/thường) với màu custom khác của chính user **và** với mọi màu system.


Grid snapshot và `layers[]` dùng `color_code` dạng `#RRGGBB` (không dùng UUID). API normalize paint/layer khi PATCH tiles và autosave layers; field legacy `color_id`/`hex` vẫn được chấp nhận và map sang `color_code`.

---



## 6. Nghiệp vụ chính



### 6.1 Tạo WorkItem — Process endpoint (duy nhất)

`POST /api/v1/work_items/` — multipart/form-data:


| Field                  | Bắt buộc | Mô tả                            |
| ---------------------- | -------- | -------------------------------- |
| `item_code`            | Có       | **Unique** toàn hệ thống         |
| `name`                 | Không    |                                  |
| `status`               | Không    | default `1` (New)                |
| `workflow_template_id` | Không    | default template `STANDARD_SHOE` |
| `files[]`              | Có       | ≥1 file PDF/AI/DXF               |


**Pipeline** (`core/services/work_item_process.py`):

1. Validate `item_code` unique.
2. Tạo `WorkItem` + gán workflow template.
3. Với mỗi file: `create_source_document()` → lưu `FileObject`.
4. `process_source_document_with_ai()` → part detection (hiện tại local converter, chưa gọi AI service).
5. `initialize_part_steps()` + `bootstrap_completed_part_steps()`.

**Response** (`ProcessWorkItemResultSerializer`):

```json
{
  "work_item": { ... },
  "source_documents": [ ... ],
  "parts": [ ... ]
}
```



### 6.2 Part detection (stub AI)

`core/services/part_detection.py` + `source_document_converter.py`:

1. Đọc bytes từ `FileObject`.
2. `FileToSvgConverter` convert PDF/AI/DXF → danh sách SVG string.
3. **Mỗi SVG = 1 Part**, lưu SVG làm `preview_file`.
4. Khởi tạo PartStep từ template.
5. Bootstrap bước 1 (xem §6.3).
6. Lỗi → `SourceDocument.status = FAILED`, raise ValidationError.

Dependencies design service: `pymupdf`, `ezdxf`, `matplotlib`.

### 6.3 Bootstrap step 1

`bootstrap_completed_part_steps()` tự **official complete** bước đầu tiên:


| Step          | Settings | Artifact role                           |
| ------------- | -------- | --------------------------------------- |
| RECEIVE_FILES | `{}`     | `SOURCE_FILE` → file gốc SourceDocument |


`PICK_UPPER` **không** auto-complete — user chọn upper, rotation và complete thủ công. Candidates được gợi ý sẵn trong `part.detected_metadata.pick_upper_candidates`.

User bắt đầu làm từ bước **2** (`PICK_UPPER`) qua revision service.

### 6.4 Step revision — autosave / save / complete

Service trung tâm: `create_step_revision()` (`core/services/step_revision.py`).

**Request body** (multipart khi có file):


| Field                                            | Mô tả                                |
| ------------------------------------------------ | ------------------------------------ |
| `settings`                                       | JSON object hoặc JSON string         |
| `files[]`                                        | Output files (PNG, JPG, SVG, PDF, …) |
| `base_revision_id`                               | Optional — optimistic concurrency    |
| `note`, `app_version`, `settings_schema_version` | Optional                             |



| Endpoint             | revision_type | Hành vi                                                                                        |
| -------------------- | ------------- | ---------------------------------------------------------------------------------------------- |
| `POST .../autosave/` | 1 Autosave    | Dedup nếu settings hash giống + không file mới; giữ 12 autosave gần nhất                       |
| `POST .../save/`     | 2 Manual      | Tạo revision mới                                                                               |
| `POST .../complete/` | 3 Official    | Set `official_revision`, mark step **DONE**, gọi `clear_steps_after`, trả `next_step_settings` |


**Settings wrapper** — mọi revision lưu dạng `{ data, meta }` trong DB; API GET trả `settings` (unwrap `data`) + `settings_meta` riêng.

`meta.source`: `manual` | `bootstrap` | `propagated` | `ai` | `restored` | `grid_import`.

`STEP_SETTINGS_POLICY` (`core/constant.py`) — expose qua `GET /workflow_steps/` field `settings_policy` (has_settings, input_mode, schema_key, on_complete).

**Complete response** (khi có propagate):

```json
{
  "revision": { "... StepRevisionDetail ..." },
  "next_step_settings": {
    "step_code": "CANVAS_FRAME_MEASURE",
    "settings": { "... data ..." },
    "meta": { "source": "ai", "from_step_code": "CHECK_COLORS" }
  }
}
```

**Settings validation** (`step_settings_serializers.py`):

- `PICK_UPPER`: `{ selected_candidate_index, rotation, candidates[] }`
- `FIX_LINES_BY_ANCHOR`: `{ anchors[], snap_distance, tolerance }`
- `CHECK_COLORS`: `{ layers, manual_overrides[], frame_expansion_mm, corner_type, corner_limit }`
- `CANVAS_FRAME_MEASURE`: `{ canvas{width_mm,height_mm}, origin{x,y}, scale, basis{} }`
- `ENTER_SPECS`: `{ needle_density, cos_number, course_per_pixel, grid_pixels, source_measurements_mm }` — server tính `grid_pixels` khi complete
- `BUILD_GRID`: `{ grid{width,height}, conversion{}, grid_snapshot_id }`
- `START_DESIGNING`: `{ active_file_type, progress{} }` — metadata; grid body qua DesignWorkspace

**Step complete handlers** (`core/services/step_handlers/`):


| Step complete | Handler                        | next_step_settings   |
| ------------- | ------------------------------ | -------------------- |
| CHECK_COLORS  | AI bridge (`check_colors_ai`)  | CANVAS_FRAME_MEASURE |
| ENTER_SPECS   | Grid pixel calc                | BUILD_GRID           |
| BUILD_GRID    | Grid snapshot + init workspace | START_DESIGNING      |




### 6.5 Complete step — re-complete & xóa step sau

**Không có API revert riêng.** Logic gộp vào **complete**:

Khi `POST .../steps/{step_code}/complete/`:

1. Tạo **official revision mới** (kể cả step đã DONE — **complete lại được**).
2. **Bỏ qua** kiểm tra `base_revision_id` conflict khi complete (`mark_step_done=True`).
3. Gọi `clear_steps_after(part, after_sequence=step.sequence)`:
  - Hard-delete **tất cả StepRevision** (và artifacts) của các PartStep có `step.sequence` **lớn hơn** bước vừa complete.
  - Reset các PartStep đó: `NOT_STARTED`, xóa timestamps, `latest_revision`, `official_revision`.
  - Xóa **DesignWorkspace** + blobs step 10 (nếu có).

**Ví dụ:** đã làm bước 1→5, quay lại bước 2 và complete → xóa sạch revision bước 3, 4, 5.

Implementation: `core/services/part_revert.py` → `clear_steps_after()`.

### 6.6 Restore revision

`POST /api/v1/revisions/{id}/restore/` — tạo revision mới type **RESTORE** (4), copy settings + artifacts từ revision gốc, `parent_revision` trỏ về revision cũ. Không mutate revision cũ.

### 6.7 Concurrency (autosave / save)

Nếu client gửi `base_revision_id` và **không phải complete**:

```text
base_revision_id == part_step.latest_revision_id
```

Không khớp → **409 Conflict**.

Complete **không** check conflict — cho phép ghi đè intentional.

---



## 7. API đầy đủ

Prefix: `/api/v1/`. Auth: Bearer JWT (trừ login/register/refresh).

### 7.1 Auth & Users — `user_service` :9001


| Method | Path                          | Auth   | Mô tả       |
| ------ | ----------------------------- | ------ | ----------- |
| POST   | `/api/v1/auth/register/`      | Public |             |
| POST   | `/api/v1/auth/login/`         | Public |             |
| POST   | `/api/v1/auth/logout/`        | User   |             |
| GET    | `/api/v1/auth/me/`            | User   |             |
| POST   | `/api/v1/auth/refresh/`       | Public | Body `{"refresh_token": "..."}` (key `refresh` cũ vẫn nhận) |
| GET    | `/api/v1/users/`              | Staff  | Paginated   |
| POST   | `/api/v1/users/`              | Staff  |             |
| GET    | `/api/v1/users/{id}/`         | Staff  |             |
| PATCH  | `/api/v1/users/{id}/`         | Staff  |             |
| DELETE | `/api/v1/users/{id}/`         | Staff  | Soft delete |
| POST   | `/api/v1/users/{id}/restore/` | Staff  |             |


Default users (seeder): `admin`, `designer`, `developer` — password `Defaultpassword@123`.

### 7.2 WorkItems & Design — `design_service` :9002


| Method | Path                                          | Auth  | Mô tả                                                                                  |
| ------ | --------------------------------------------- | ----- | -------------------------------------------------------------------------------------- |
| GET    | `/api/v1/work_items/`                         | User  | Paginated; filter `item_code`, `status`, `q`; mỗi item có `parts_count`                |
| POST   | `/api/v1/work_items/`                         | User  | **Process** upload + detect + bootstrap                                                |
| GET    | `/api/v1/work_items/{id}/`                    | User  | Detail: nested `source_documents` + `parts`                                            |
| PATCH  | `/api/v1/work_items/{id}/`                    | User  | `name`, `status`, `workflow_template_id`                                               |
| DELETE | `/api/v1/work_items/{id}/`                    | User  |                                                                                        |
| GET    | `/api/v1/work_items/{id}/source_documents/`   | User  | Paginated                                                                              |
| GET    | `/api/v1/work_items/{id}/parts/`              | User  | **Tất cả parts, không phân trang**                                                     |
| GET    | `/api/v1/source_documents/{id}/`              | User  |                                                                                        |
| DELETE | `/api/v1/source_documents/{id}/`              | User  |                                                                                        |
| GET    | `/api/v1/source_documents/{source_id}/parts/` | User  | Paginated                                                                              |
| GET    | `/api/v1/parts`                               | User  | Part của mọi work item đã tới START_DESIGNING (BUILD_GRID `done`). Phân trang. Filter `q` (name, icontains), `created_from`, `created_to` (`YYYY-MM-DD`, inclusive). Ngày không hợp lệ → trang rỗng |
| POST   | `/api/v1/parts/`                              | Staff | Bulk create. Multipart: `source_document_id` một lần, `previews` lặp mỗi part. `name` = `New part 1`, `New part 2`, … (nối tiếp số part đã có). `sequence` = max+1, +2, …; init steps như import (RECEIVE_FILES DONE) |
| GET    | `/api/v1/parts/{id}/`                         | User  | Part detail + nested source_document + file URL                                        |
| PATCH  | `/api/v1/parts/{id}/`                         | Staff | `name`, `status`; multipart field `preview` để thay ảnh part (khi import PDF sai vùng) |
| DELETE | `/api/v1/parts/`                              | Staff | Bulk delete. Body `{"ids": ["uuid", ...]}`. Xóa từng part + steps + revisions + workspace bước 10; dọn blob không còn tham chiếu; id không tồn tại thì hủy cả request; không đánh lại `sequence` |
| GET    | `/api/v1/workflow_templates/`                 | Staff |                                                                                        |
| POST   | `/api/v1/workflow_templates/`                 | Staff |                                                                                        |
| GET    | `/api/v1/workflow_templates/{id}/`            | Staff |                                                                                        |
| PATCH  | `/api/v1/workflow_templates/{id}/`            | Staff |                                                                                        |
| POST   | `/api/v1/workflow_templates/{id}/sync-parts/` | Staff | Sync PartStep cho mọi Part                                                             |
| GET    | `/api/v1/workflow_steps/`                     | User  |                                                                                        |
| POST   | `/api/v1/workflow_steps/`                     | Staff |                                                                                        |
| GET    | `/api/v1/workflow_steps/{id}/`                | User  |                                                                                        |
| PATCH  | `/api/v1/workflow_steps/{id}/`                | Staff |                                                                                        |


**Máy dệt** (`design_service`). Chỉ lưu catalog ô xám liên kết với nhau. Hai bảng:

1. `weaving_machine` — `name`, `type` (`Single` hoặc `Double`), `jacquard` (`1` hoặc `2`), `max_bars`, và các dòng barre (`bar_no`, `bar_code`, `zul_max_kg`, `max_versatzsprung`, `max_ueberlegungssprung`, `ns` là số cơ). `max_bars` và bảng barre theo **machine name**, không theo width.
2. `weaving_machine_spec` — một dòng là một bộ ba `machine` + `needles_per_inch` (n/inch) + `width`.

FE: chọn name → các gauge là `needles_per_inch` phân biệt trong spec của máy đó → chọn gauge → các `width` của cặp name+gauge → chọn width là xong bộ ba. Màn barre đọc `max_bars` và `bars` của machine name. Chu kỳ chain-link khi tạo file KMO do FE lưu; BE không giữ lưới kim.

| Method | Path | Auth | Mô tả |
| ------ | ---- | ---- | ----- |
| GET/POST | `/api/v1/weaving_machines` | User / Staff | Danh sách / tạo máy (`name`, `type` Single\|Double, `jacquard` 1\|2, `max_bars` và `bars` tùy chọn) |
| GET/PATCH/DELETE | `/api/v1/weaving_machines/{id}` | User / Staff | Name, type, jacquard, max_bars, specs, bars. PATCH `bars` thay toàn bộ barre |
| GET/POST | `/api/v1/weaving_machines/{id}/specs` | User / Staff | Gauge+width của **đúng máy** `{id}`. Query `needles_per_inch` chỉ lọc width của gauge đó trên máy này. Không có list spec theo gauge toàn cục |
| GET/PATCH/DELETE | `/api/v1/weaving_machine_specs/{id}` | User / Staff | Một dòng gauge + width |
| GET/POST | `/api/v1/weaving_machines/{id}/bars` | User / Staff | Barre của **đúng máy** `{id}`. Không có list barre toàn cục |
| GET/PATCH/DELETE | `/api/v1/weaving_machine_bars/{id}` | User / Staff | Một barre |


### 7.3 Part workflow & Revisions — `revision_service` :9003


| Method | Path                                                               | Auth  | Mô tả                                                                                        |
| ------ | ------------------------------------------------------------------ | ----- | -------------------------------------------------------------------------------------------- |
| GET    | `/api/v1/parts/{id}/steps/`                                        | User  | List PartStep theo sequence                                                                  |
| POST   | `/api/v1/parts/{id}/sync-steps/`                                   | Staff | Sync từ template                                                                             |
| GET    | `/api/v1/parts/{id}/steps/{step_code}/`                            | User  | Detail + latest/official revision + artifacts                                                |
| GET    | `/api/v1/parts/{id}/steps/{step_code}/revisions/`                  | User  | Paginated; filter `revision_type`                                                            |
| POST   | `/api/v1/parts/{id}/steps/{step_code}/autosave/`                   | Staff |                                                                                              |
| POST   | `/api/v1/parts/{id}/steps/{step_code}/save/`                       | Staff |                                                                                              |
| POST   | `/api/v1/parts/{id}/steps/{step_code}/complete/`                   | Staff | Official + clear steps after                                                                 |
| GET    | `/api/v1/revisions/{id}/`                                          | User  |                                                                                              |
| POST   | `/api/v1/revisions/{id}/restore/`                                  | Staff |                                                                                              |
| GET    | `/api/v1/parts/{id}/steps/START_DESIGNING/workspace`              | User  | Workspace + 8 file chính rồi đến file nháp. Mỗi revision có `snapshot_file` (gzip) |
| GET    | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}`           | User  | Official/latest revision summary                                                             |
| GET    | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}/revisions` | User  | Revision history                                                                             |
| POST   | `/api/v1/parts/{id}/steps/START_DESIGNING/drafts`                 | Staff | Body bắt buộc `name`, `width`, `height`. Tạo file nháp `D1`, `D2`, … và revision 1 (gzip rỗng) để GET tiles ngay. Không nằm trong flow S–KMO |
| DELETE | `/api/v1/parts/{id}/steps/START_DESIGNING/drafts/{file_type}`     | Staff | Xóa file nháp và toàn bộ revision. File S–KMO không xóa được                                 |
| POST   | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}/reopen`    | Staff | Mở lại file chính đã complete (ví dụ S1). File đó và các file sau đang `done` về `in_progress`, `official_revision` = null. Nếu step 10 đã done thì về in progress |
| POST   | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}/autosave/`  | Staff | Design file autosave (`layers`). File nháp (`D1`…) cùng cách với S, không kiểm tra file trước đã complete |
| POST   | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}/save/`      | Staff | Design file manual save (`revision_type=2`)                                                  |
| POST   | `/api/v1/parts/{id}/steps/START_DESIGNING/files/{type}/complete/`  | Staff | Đánh official + cập nhật `progress`; không đọc `tile_manifest`, không vẽ preview; complete KMO → done step 10 |
| GET    | `/api/v1/design_file_revisions/{id}/tiles/?x0&y0&x1&y1`            | User  | Viewport tile load (**S và file nháp**)                                                      |
| PATCH  | `/api/v1/design_file_revisions/{id}/tiles/`                        | Staff | Batch tile upload (**S và file nháp**). Lưu nguyên `data` (base64 gzip hoặc base64 JSON), không giải nén, không ghi `tile_manifest`, không vẽ preview. GET trả lại đúng chuỗi đó. Optional `grid_width` + `grid_height` để đổi kích thước |
| POST   | `/api/v1/design_file_revisions/{id}/restore/`                      | Staff | Restore design file revision                                                                 |
| POST   | `/api/v1/ai/smart_s`                                               | Staff | FE gửi `svg_id`. BE render PNG URL (`BE_DOMAIN/media/...`) rồi gọi `AI_DOMAIN/api/v1/smart_s` với `url_svg` |
| POST   | `/api/v1/ai/merge_images`                                          | Staff | FE gửi `list_image_ids[]`. BE gọi AI với `list_url_images`. `background` `white`/`black` |
| POST   | `/api/v1/ai/create_files_c`                                        | Staff | FE gửi `image_id`. BE gọi `AI_DOMAIN/api/v1/create_files_c` với `url_image` |
| POST   | `/api/v1/ai/create_file_p`                                         | Staff | FE gửi `l_id`, `r_id`, `l_f_id`, `r_f_id`. BE gửi `url_l`, `url_r`, `url_l_f`, `url_r_f` |
| POST   | `/api/v1/ai/split_regions`                                         | Staff | Passthrough `url_path` + `product_code` → `AI_DOMAIN/api/v1/split_regions` |
| POST   | `/api/v1/ai/rotate_svg`                                            | Staff | Passthrough `url_svg` + `product_code` → `AI_DOMAIN/api/v1/rotate_svg` |
| POST   | `/api/v1/ai/delete_paths`                                          | Staff | Passthrough `url_svg` + `product_code` → `AI_DOMAIN/api/v1/delete_paths` |
| POST   | `/api/v1/ai/delete_anchors`                                        | Staff | Passthrough `url_svg` + `product_code` → `AI_DOMAIN/api/v1/delete_anchors` |
| POST   | `/api/v1/ai/color_paths`                                           | Staff | Passthrough `url_svg` + `product_code` → `AI_DOMAIN/api/v1/color_paths` |
| POST   | `/api/v1/ai/create_train_db`                                       | Staff | Passthrough `url_svg`, `index_list[]`, `type` → `AI_DOMAIN/api/v1/create_train_db` |
| POST   | `/api/v1/ai/create_train_db_anchor`                                | Staff | Passthrough `url_svg`, `index_list` cặp `[path_index, point_index]` → `AI_DOMAIN/api/v1/create_train_db_anchor` |
| POST   | `/api/v1/ai/create_file_fc`                                        | Staff | FE gửi `image_id` (+ `product_code`, `count`, `type_machine` tùy chọn). BE gửi `url_image` tới `AI_DOMAIN/api/v1/create_file_fc` |
| POST   | `/api/v1/ai/auto_job`                                              | Staff | FE gửi `image_id`, `product_code`; `type_machine`, `number_jackquard` tùy chọn. BE gửi `url_image` |
| POST   | `/api/v1/ai/combine_fc`                                            | Staff | FE gửi `ff_id`, `fb_id`. BE gửi `url_ff`, `url_fb`. `ff_has_hole`, `fb_has_hole` mặc định false |
| POST   | `/api/v1/ai/shift_odd_rows`                                        | Staff | FE gửi `image_id`, `value`. BE gửi `url_image`, `value` |
| POST   | `/api/v1/ai/create_kmo`                                            | Staff | FE gửi `image_id`. BE gửi `url_image`. `name_machine`, `gauge`, `width`, `rt`, `product_code`, `course_per_pixel`, `kmo_has_valve_chain` tùy chọn |
| GET    | `/api/v1/colors/`                                                  | User  | System block (theo `display_order`) + custom block của user (theo `display_order`)           |
| POST   | `/api/v1/colors/`                                                  | Staff | Tạo màu custom: `code`, `hex_value` bắt buộc; `name`, `display_order` optional               |
| PATCH  | `/api/v1/colors/{id}/`                                             | Staff | Sửa màu custom (`code`, `hex_value`, `name`, `display_order`); id system → 400               |
| DELETE | `/api/v1/colors/{id}/`                                             | Staff | Xóa màu custom; id system → 400                                                              |
| GET    | `/api/v1/system_colors/`                                           | User  | Danh sách màu system                                                                         |
| GET    | `/api/v1/system_colors/{id}/`                                      | User  | Chi tiết màu system                                                                          |
| POST   | `/api/v1/system_colors/`                                           | Admin/Developer | Thêm màu system: `code`, `hex_value`, `name` bắt buộc; `display_order` optional    |
| PATCH  | `/api/v1/system_colors/{id}/`                                      | Admin/Developer | Sửa `code`, `hex_value`, `name`, `display_order`                                   |
| DELETE | `/api/v1/system_colors/{id}/`                                      | Admin/Developer | Xóa màu system                                                                     |


**Design file sequence:** `S → S1 → C → H → P → F → FC → KMO` (`DESIGN_FILE_SEQUENCE`). Tên file: `{item_code}_S.png`, `{item_code}_S1.png`, … `{item_code}.kmo`. **BUILD_GRID** tạo revision 1 của file **S** với grid snapshot trống kích thước `settings.grid.width × height` + preview PNG. Kích thước này **chỉ áp dụng cho revision đầu tiên**: FE đổi kích thước bất kỳ lúc nào bằng `PATCH tiles` với `grid_width` + `grid_height` (BE xóa tile cũ, ghi tile mới theo size mới); revision tạo sau đó copy kích thước từ revision latest. `workspace.settings.grid` chỉ là kích thước ban đầu. Mỗi paint trong cell giữ `color_code`, `order`, `is_hidden`, `is_lock`. **Không khóa file** — FE mở/xem/edit tab tự do. **Complete** file chính phải đúng thứ tự: BE trả 400 nếu file trước chưa `progress=done` (vd. `"Complete S before S1!"`). File nháp (`is_draft`, `file_type` `D1`, `D2`, …) lưu và complete không kiểm tra thứ tự, không đổi `progress` của S–KMO, và xóa được. Complete lại **BUILD_GRID** xóa revision của mọi file và xóa luôn các file nháp. Tạo nháp bắt buộc `name`, `width`, `height`: BE tạo revision 1 với gzip snapshot trống đúng kích thước đó để FE gọi GET tiles ngay, rồi PATCH tiles và autosave/save `layers[]` giống **S**. Workspace trả `snapshot_file` (gzip) trên `latest_revision` và `official_revision`. `POST .../files/{type}/reopen` mở lại một file chính đã complete: file đó và mọi file sau đang `done` về `in_progress`, `official_revision` của các file từ file đó đến KMO về `null`, `active_file_type` trỏ về file vừa mở. Nếu step 10 đã done thì về in progress. `S1`–`KMO` không dùng tiles.

Seed colors: `python manage.py seed_system_colors`.

### 7.4 API đã **loại bỏ** (không còn trong code)


| API cũ                                             | Thay thế                                                |
| -------------------------------------------------- | ------------------------------------------------------- |
| `POST /work_items/{id}/source_documents/`          | Gộp vào `POST /work_items/` (process)                   |
| `POST /source_documents/{id}/complete-processing/` | Gộp vào process pipeline                                |
| JSON-only `POST /work_items/` (không file)         | Bắt buộc multipart + `files[]`                          |
| `POST /parts/{id}/revert/`                         | **Không có** — dùng complete step + `clear_steps_after` |


---



## 8. Serializers (response shape)



### WorkItem


| Serializer                        | Dùng cho                                                         |
| --------------------------------- | ---------------------------------------------------------------- |
| `WorkItemSerializer`              | List, update response — có `parts_count`, `workflow_template_id` |
| `WorkItemDetailSerializer`        | GET detail — thêm `source_documents[]`, `parts[]`                |
| `ProcessWorkItemResultSerializer` | POST create — `{ work_item, source_documents, parts }`           |




### Part / SourceDocument


| Serializer                 | Ghi chú                        |
| -------------------------- | ------------------------------ |
| `SourceDocumentSerializer` | Nested `file` với `url`        |
| `PartSerializer`           | `work_item_id`, `preview_file` |
| `PartDetailSerializer`     | + nested `source_document`     |




### Revision


| Serializer                     | Ghi chú                   |
| ------------------------------ | ------------------------- |
| `PartStepSerializer`           | Summary latest/official   |
| `PartStepDetailSerializer`     | Full revision + artifacts |
| `StepRevisionDetailSerializer` | + `artifacts[]`           |
| `SaveStepRevisionSerializer`   | Write: settings + files   |




### File

`FileObjectSerializer` — field `url` build từ `BE_DOMAIN` + `storage_key`.

---



## 9. Permissions

```python
STAFF_ROLES = (Developer=1, Admin=2, Designer=4)  # Customer=3 không thuộc staff
ADMIN_ROLES = DESIGN_ROLES = STAFF_ROLES  # tạm thời staff có quyền như nhau
```


| Helper                               | Áp dụng                                       |
| ------------------------------------ | --------------------------------------------- |
| `require_admin` / `can_manage_users` | User CRUD, workflow template/step admin       |
| `require_design`                     | sync-steps, autosave, save, complete, restore |
| `require_system_color_admin`         | POST/PATCH/DELETE `/system_colors` — chỉ Developer, Admin (`SYSTEM_COLOR_ADMIN_ROLES`, không gồm Designer) |
| Authenticated user                   | Đọc hầu hết design/revision data              |


Public paths: `api/v1/auth/login`, `register`, `refresh`.

---



## 10. File storage


| Biến                     | Ví dụ                             | Mô tả                                  |
| ------------------------ | --------------------------------- | -------------------------------------- |
| `BE_DOMAIN`              | `http://192.168.0.134:82`         | Prefix URL file (phải khớp port nginx) |
| `FORWARD_PORT`           | `82`                              | Host port nginx → container 80         |
| `MEDIA_URL`              | `/media/`                         |                                        |
| `FILE_STORAGE_ROOT`      | `/usr/src/service/media` (Docker) |                                        |
| `OBJECT_STORAGE_BACKEND` | `1`                               | 1=Local, 3=MinIO, 4=S3                 |


**URL file:** `http://192.168.0.134:82/media/objects/ab/abc123....pdf`

**Dedup:** cùng `(sha256, size_bytes)` → reuse `FileObject`; không overwrite storage key cũ.

Mỗi service có `.env` riêng (`services/design/.env`, …) — Docker mount file đó; `BE_DOMAIN` **phải set trong từng service .env**.

---



## 11. Migrations


| Migration                        | Nội dung                                                   |
| -------------------------------- | ---------------------------------------------------------- |
| `0001_initial`                   | Toàn bộ schema ban đầu                                     |
| `0002_workflowtemplate_and_more` | WorkflowTemplate, TemplateStep, WorkItem.workflow_template |
| `0003_workitem_item_code_unique` | `WorkItem.item_code` → **unique=True**                     |


Chạy: `docker compose exec design_service python manage.py migrate` (và tương tự revision/user nếu cần).

---



## 12. Docker & phát triển

```bash
cd paihong_apis
docker compose up -d
# Rebuild design sau khi đổi converter deps:
docker compose build design_service && docker compose up -d design_service
```

Swagger: `/api/schema/swagger-ui/` trên từng service port.

**Gọi API khuyến nghị:**

- Dev trực tiếp: `http://192.168.0.134:9001|9002|9003/api/v1/...` (underscore paths).
- Qua nginx: `http://192.168.0.134:82/...` (kiểm tra path hyphen vs underscore).

---



## 13. Ghi chú triển khai / thay đổi gần đây

Tóm tắt các thay đổi đã implement (sync với source hiện tại):

1. **Process WorkItem** — một endpoint POST thay cho upload/complete tách rời.
2. **FileToSvgConverter** — detect Part local (PDF/AI/DXF → SVG); mỗi SVG = 1 Part.
3. **Bootstrap** RECEIVE_FILES auto-DONE khi tạo Part; PICK_UPPER do user complete.
4. **Complete step** gộp logic “revert”: xóa revision các step sau; **complete lại step đã DONE được**.
5. **Không có API revert** riêng.
6. `item_code` **unique** — DB + serializer validation.
7. `BE_DOMAIN` — URL file trả về đúng IP/host (kèm `:82` nếu nginx map port 82).
8. **WorkItem detail** — nested source_documents + parts.
9. **WorkItem list** — thêm `parts_count`.
10. **WorkItem parts sub-route** — không phân trang.
11. `get_instance()` — hỗ trợ cả Model class và QuerySet (select_related/prefetch).
12. **Permissions** — Developer, Admin, Designer có quyền staff tương đương.

---



## 14. Checklist cho AI / developer mới

- [ ] Dùng **integer enum** khi đọc/ghi status fields.
- [ ] Timestamps: `created` **/** `modified`.
- [ ] Upload source chỉ qua `POST /api/v1/work_items/` với `files[]`.
- [ ] Revision write cần role **staff** (designer/admin/developer).
- [ ] Complete = official revision + **xóa data step sau**.
- [ ] File URL cần `BE_DOMAIN` đúng trong service `.env`.
- [ ] Không implement lại API revert — đã bỏ.
- [ ] Source extensions: **pdf, ai, dxf** (không có dwg trong code).

---

*Tài liệu cập nhật theo source backend* `paihong_apis/` *— phản ánh implementation thực tế, không phải spec draft cũ.*