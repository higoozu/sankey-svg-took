# Sankey SVG Tool (macOS + Windows)

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

## 本地构建

普通构建：

```bash
npm run tauri:build
```

Universal 构建（Apple Silicon + Intel）：

```bash
npm run tauri:build -- --target universal-apple-darwin
```

构建产物目录：`src-tauri/target/`。

### Windows（本机在 Windows 时）

```bash
npm run tauri:build -- --bundles nsis
```

## GitHub Actions 自动打包

仓库已提供工作流：

- `.github/workflows/build-desktop.yml`
- 支持两种触发：
  - 手动触发：`Actions -> Build Desktop Apps -> Run workflow`
  - 打 tag 触发：如 `v0.1.1`

该工作流会构建并上传：

- `macos-universal-bundles`：`.app` + `.dmg`
- `windows-nsis-bundle`：Windows 安装包 `.exe`
