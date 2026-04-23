# 第 6 章：安装包模块（`apps/packages`）

本章说明：**如何在系统里建「版本」、上传文件、这些文件和部署任务怎么关联**。目录：`apps/packages/`。

---

## 1. 为什么要单独做一个「安装包管理」？

部署任务执行时，可能需要把 **TPOPS 主包、内核包** 等传到现场机的 **`部署根/pkgs/`**。  
这些文件往往很大，需要：

- **在本系统磁盘上存一份**（`FileField` → `media/packages/...`）；  
- **在数据库里记文件名、大小、哈希、属于哪个版本**；  
- 创建任务时只传 **ID 列表**，后台按 ID 找到本地路径再 SFTP。

---

## 2. 两个层级：Release（版本）与 Artifact（文件）

- **PackageRelease**：逻辑上的「一组包」，例如「TPOPS-某版本介质」。  
- **PackageArtifact**：这一组里的**单个文件**；必须挂在一个 `release` 下。

**小白类比**：Release 像「专辑」，Artifact 像「专辑里的一首歌文件」。

---

## 3. API 行为

### 版本 `/api/packages/releases/`

| 方法 | 作用 |
|------|------|
| GET | 列出你有权限看到的版本 |
| POST | 新建版本 |
| GET `/releases/<id>/` | 详情 |
| DELETE | 删除版本（会级联删掉下属所有 artifact 及磁盘文件） |

### 文件 `/api/packages/artifacts/`

| 方法 | 作用 |
|------|------|
| GET `?release=<id>` | 列出该版本下所有已上传文件 |
| POST | **multipart 上传**；可不手写 `remote_basename`，服务端会从 `original_name` 生成安全文件名 |
| DELETE `/artifacts/<id>/` | 删库记录并删物理文件 |

实现：**`views.py`** + **`serializers.py`**；路径与安全文件名规则在 **`models.py`**（`_safe_remote_basename`）。

---

## 4. 与部署向导的关系

前端向导里「选版本 → 勾选要同步的类别 → 选具体文件」后，会把选中的 **artifact 主键列表** 写进任务的 **`package_artifact_ids`**，并带上 **`package_release`**。  
后台 **`runner._sync_pkgs_to_remote`** 根据这些 ID 读本地文件并上传。

---

## 5. 小白常见疑问

**Q：上传失败 400？**  
A：看返回 JSON；常见是字段校验问题。当前创建 serializer 已允许 `remote_basename` 可选。

**Q：远端文件名和本地不一样？**  
A：以 **`remote_basename`** 为准；由原始文件名清洗得到。

---

上一章：[部署模块](05-deployment-module.md)  
下一章：[清单模块 manifest](07-manifest-module.md)
