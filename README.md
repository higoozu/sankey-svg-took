# Sankey SVG Tool (macOS)

轻量桌面工具：导入 `.xlsx`，支持 2-4 层字段映射，生成桑基图并导出可分层编辑的 `.svg`。

## 功能

- 拖拽或手动选择 `.xlsx`
- 选择 `Sheet`
- 可配置 2/3/4 层字段映射
- 聚合方式：`sum` / `count`
- 最小流量过滤、画布尺寸、节点宽度、节点间距
- 导出 SVG，包含分层组：
  - `g#layer-links`
  - `g#layer-nodes`
  - `g#layer-labels`

## 运行环境

- Node.js 20+
- Rust（用于 Tauri）

### 安装 Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

安装后重开终端，确认：

```bash
cargo -V
```

## 开发

```bash
npm install
npm run tauri:dev
```

## 构建 mac App / DMG

普通构建：

```bash
npm run tauri:build
```

Universal 构建（Apple Silicon + Intel）：

```bash
npm run tauri:build -- --target universal-apple-darwin
```

构建产物目录：`src-tauri/target/`。

## 与原脚本关系

原始脚本 `桑基图.py` 的逻辑是固定 `纬度 -> 领域 -> 行业` 三层，本工具扩展为 2-4 层可配置映射，并提供图形界面与分层 SVG 导出。
