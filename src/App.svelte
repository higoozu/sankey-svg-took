<script lang="ts">
  import * as XLSX from 'xlsx';
  import { sankey, sankeyLinkHorizontal } from 'd3-sankey';

  type Row = Record<string, unknown>;

  type NodeData = {
    id: string;
    name: string;
    layer: number;
    color: string;
  };

  type LinkData = {
    source: string;
    target: string;
    value: number;
    layer: number;
  };

  type SankeyNode = NodeData & {
    x0: number;
    x1: number;
    y0: number;
    y1: number;
    value?: number;
  };

  type SankeyLink = LinkData & {
    width: number;
    y0: number;
    y1: number;
  };

  let fileName = '';
  let workbook: XLSX.WorkBook | null = null;
  let sheetNames: string[] = [];
  let selectedSheet = '';
  let rows: Row[] = [];
  let columns: string[] = [];
  let errorMsg = '';
  let dragActive = false;

  let levelsCount = 3;
  let levelColumns: string[] = ['', '', ''];
  let valueColumn = '';

  let aggMode: 'sum' | 'count' = 'sum';
  let minValue = 0;

  let width = 1600;
  let height = 900;
  let nodeWidth = 18;
  let nodePadding = 16;
  let decimals = 2;
  let canGenerate = false;

  let graphNodes: SankeyNode[] = [];
  let graphLinks: SankeyLink[] = [];
  let hasGraph = false;

  let svgEl: SVGSVGElement | null = null;
  let fileInputEl: HTMLInputElement | null = null;

  const layerPalette = ['#1570EF', '#12B76A', '#F79009', '#EE46BC', '#444CE7', '#039855'];
  const linkPath = sankeyLinkHorizontal();

  $: if (levelColumns.length !== levelsCount) {
    levelColumns = Array.from({ length: levelsCount }, (_, i) => levelColumns[i] || '');
  }

  $: canGenerate = !!rows.length && !!valueColumn && levelColumns.every(Boolean);

  function normalizeText(value: unknown): string {
    if (value === null || value === undefined) return '';
    return String(value).trim();
  }

  function escapeXml(raw: string): string {
    return raw
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&apos;');
  }

  async function onFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      await loadWorkbook(file);
    }
  }

  async function onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = false;
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      await loadWorkbook(file);
      return;
    }
    errorMsg = '未识别到可读取的文件，请尝试点击“选择 xlsx”。';
  }

  function onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = true;
  }

  function onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = false;
  }

  function openFilePicker() {
    fileInputEl?.click();
  }

  function onDropzoneKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openFilePicker();
    }
  }

  async function loadWorkbook(file: File) {
    errorMsg = '';
    hasGraph = false;

    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      errorMsg = '仅支持 .xlsx 文件。';
      return;
    }

    try {
      fileName = file.name;
      const buffer = await file.arrayBuffer();
      workbook = XLSX.read(buffer, { type: 'array' });
      sheetNames = workbook.SheetNames;
      selectedSheet = sheetNames[0] || '';
      parseSheet();
    } catch (error) {
      errorMsg = `读取文件失败：${(error as Error).message}`;
    }
  }

  function parseSheet() {
    if (!workbook || !selectedSheet) return;

    const sheet = workbook.Sheets[selectedSheet];
    const parsed = XLSX.utils.sheet_to_json<Row>(sheet, { defval: '' });

    rows = parsed;
    columns = Array.from(new Set(parsed.flatMap((row) => Object.keys(row))));

    autoMapColumns();
    hasGraph = false;
  }

  function autoMapColumns() {
    if (!columns.length) return;

    const preferredLevels = ['纬度', '领域', '行业'];
    const preferredValue = ['风险指数', '值', 'value', 'score'];

    levelColumns = Array.from({ length: levelsCount }, (_, idx) => {
      const hit = preferredLevels[idx] && columns.find((c) => c === preferredLevels[idx]);
      if (hit) return hit;
      return columns[idx] || '';
    });

    valueColumn = preferredValue
      .map((target) => columns.find((c) => c.toLowerCase() === target.toLowerCase()))
      .find(Boolean) || columns[levelsCount] || columns[columns.length - 1] || '';
  }

  function buildGraph() {
    errorMsg = '';

    if (!canGenerate) {
      errorMsg = '请先完成层级列和值列映射。';
      return;
    }

    const linkMap = new Map<string, { source: string; target: string; value: number; layer: number }>();
    const nodeMap = new Map<string, NodeData>();

    for (const row of rows) {
      const labels = levelColumns.map((column) => normalizeText(row[column]));
      if (labels.some((x) => !x)) continue;

      let rowValue = 1;
      if (aggMode === 'sum') {
        const raw = Number(row[valueColumn]);
        if (!Number.isFinite(raw)) continue;
        rowValue = raw;
      }

      for (let layer = 0; layer < labels.length; layer += 1) {
        const key = `${layer}::${labels[layer]}`;
        if (!nodeMap.has(key)) {
          nodeMap.set(key, {
            id: key,
            name: labels[layer],
            layer,
            color: layerPalette[layer % layerPalette.length]
          });
        }
      }

      for (let i = 0; i < labels.length - 1; i += 1) {
        const source = `${i}::${labels[i]}`;
        const target = `${i + 1}::${labels[i + 1]}`;
        const mapKey = `${source}-->${target}`;

        const prev = linkMap.get(mapKey);
        if (prev) {
          prev.value += rowValue;
        } else {
          linkMap.set(mapKey, { source, target, value: rowValue, layer: i });
        }
      }
    }

    const links = Array.from(linkMap.values()).filter((link) => link.value >= minValue);
    const usedNodeIds = new Set<string>(links.flatMap((link) => [link.source, link.target]));
    const nodes = Array.from(nodeMap.values()).filter((node) => usedNodeIds.has(node.id));

    if (!nodes.length || !links.length) {
      hasGraph = false;
      errorMsg = '没有可绘制的数据，请检查映射列或筛选条件。';
      return;
    }

    const layout = sankey<NodeData, LinkData>()
      .nodeId((d) => d.id)
      .nodeWidth(nodeWidth)
      .nodePadding(nodePadding)
      .extent([
        [22, 22],
        [Math.max(100, width - 22), Math.max(100, height - 22)]
      ]);

    const output = layout({
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({ ...l }))
    });

    graphNodes = output.nodes as SankeyNode[];
    graphLinks = output.links as SankeyLink[];
    hasGraph = true;
  }

  function getLinkPath(link: SankeyLink): string {
    return String(linkPath(link as never));
  }

  function downloadSvg() {
    if (!svgEl || !hasGraph) return;

    const serializer = new XMLSerializer();
    const svgText = serializer.serializeToString(svgEl);
    const hasXmlns = /<svg\b[^>]*\sxmlns=/.test(svgText);
    const wrapped = hasXmlns
      ? svgText
      : svgText.startsWith('<svg')
        ? svgText.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
        : svgText;

    const blob = new Blob([wrapped], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const stamp = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const ts = `${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}_${pad(stamp.getHours())}${pad(stamp.getMinutes())}`;
    const baseName = fileName.replace(/\.xlsx$/i, '') || 'sankey';

    const a = document.createElement('a');
    a.href = url;
    a.download = `${baseName}_${ts}.svg`;
    a.click();

    URL.revokeObjectURL(url);
  }
</script>

<svelte:window on:dragover|preventDefault on:drop|preventDefault />

<main>
  <div class="title-row">
    <h1>Sankey SVG Tool</h1>
    <div class="author">by muffin 2026.03</div>
  </div>
  <p class="subtitle">点击导入 xlsx，会根据表头自动映射，支持 2-4 层，生成 SVG 可分层。</p>

  <div class="layout">
    <div class="card">
      <h2 class="section-title">1) 数据导入</h2>

      <div
        class="dropzone {dragActive ? 'active' : ''}"
        role="button"
        tabindex="0"
        on:click={openFilePicker}
        on:keydown={onDropzoneKeyDown}
        on:dragover={onDragOver}
        on:dragleave={onDragLeave}
        on:drop={onDrop}
      >
        <div>拖拽 .xlsx 到此处</div>
        <div class="small">或点击按钮手动选择</div>
        <div style="margin-top: 10px;">
          <button type="button" on:click|stopPropagation={openFilePicker}>选择 xlsx</button>
          <input bind:this={fileInputEl} id="file-picker" type="file" accept=".xlsx" on:change={onFileSelect} />
        </div>
      </div>

      <div class="small" style="margin-top: 8px;">当前文件：{fileName || '未选择'}</div>

      {#if sheetNames.length > 0}
        <div class="field" style="margin-top: 10px;">
          <label>Sheet</label>
          <select bind:value={selectedSheet} on:change={parseSheet}>
            {#each sheetNames as name}
              <option value={name}>{name}</option>
            {/each}
          </select>
        </div>
      {/if}

      <h2 class="section-title" style="margin-top: 14px;">2) 字段映射</h2>
      <div class="field">
        <label>层级数（2-4）</label>
        <select bind:value={levelsCount}>
          <option value={2}>2 层</option>
          <option value={3}>3 层</option>
          <option value={4}>4 层</option>
        </select>
      </div>

      {#each Array.from({ length: levelsCount }, (_, i) => i) as i}
        <div class="field">
          <label>第 {i + 1} 层列名</label>
          <select bind:value={levelColumns[i]}>
            <option value="">请选择</option>
            {#each columns as col}
              <option value={col}>{col}</option>
            {/each}
          </select>
        </div>
      {/each}

      <div class="field">
        <label>数值列</label>
        <select bind:value={valueColumn}>
          <option value="">请选择</option>
          {#each columns as col}
            <option value={col}>{col}</option>
          {/each}
        </select>
      </div>

      <h2 class="section-title" style="margin-top: 14px;">3) 参数与导出</h2>

      <div class="field">
        <label>聚合方式</label>
        <select bind:value={aggMode}>
          <option value="sum">sum（按数值列求和）</option>
          <option value="count">count（每行计数）</option>
        </select>
      </div>

      <div class="grid-2">
        <div class="field">
          <label>最小流量</label>
          <input type="number" min="0" step="0.1" bind:value={minValue} />
        </div>
        <div class="field">
          <label>小数位</label>
          <input type="number" min="0" max="6" step="1" bind:value={decimals} />
        </div>
      </div>

      <div class="grid-2">
        <div class="field">
          <label>宽度</label>
          <input type="number" min="600" step="10" bind:value={width} />
        </div>
        <div class="field">
          <label>高度</label>
          <input type="number" min="400" step="10" bind:value={height} />
        </div>
      </div>

      <div class="grid-2">
        <div class="field">
          <label>节点宽</label>
          <input type="number" min="8" max="48" step="1" bind:value={nodeWidth} />
        </div>
        <div class="field">
          <label>节点间距</label>
          <input type="number" min="2" max="48" step="1" bind:value={nodePadding} />
        </div>
      </div>

      <div class="button-row">
        <button type="button" on:click={buildGraph} disabled={!canGenerate}>生成图表</button>
        <button type="button" class="secondary" on:click={downloadSvg} disabled={!hasGraph}>导出 SVG</button>
      </div>

      {#if errorMsg}
        <p class="error">{errorMsg}</p>
      {/if}
    </div>

    <div class="card preview-wrap">
      <h2 class="section-title">预览</h2>
      {#if hasGraph}
        <svg bind:this={svgEl} viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
          <g id="layer-links">
            {#each graphLinks as link, i}
              <path
                id={`link-${i}`}
                class="sankey-link"
                data-layer={String(link.layer)}
                d={getLinkPath(link)}
                stroke={layerPalette[link.layer % layerPalette.length]}
                stroke-opacity="0.35"
                stroke-width={Math.max(1, link.width)}
                fill="none"
              />
            {/each}
          </g>

          <g id="layer-nodes">
            {#each graphNodes as node}
              <rect
                id={`node-${escapeXml(node.id)}`}
                class="sankey-node"
                data-layer={String(node.layer)}
                x={node.x0}
                y={node.y0}
                width={Math.max(1, node.x1 - node.x0)}
                height={Math.max(1, node.y1 - node.y0)}
                fill={node.color}
                fill-opacity="0.9"
                rx="2"
              />
            {/each}
          </g>

          <g id="layer-labels">
            {#each graphNodes as node}
              <text
                class="sankey-label"
                data-layer={String(node.layer)}
                x={node.x0 < width / 2 ? node.x1 + 6 : node.x0 - 6}
                y={(node.y0 + node.y1) / 2}
                dominant-baseline="middle"
                text-anchor={node.x0 < width / 2 ? 'start' : 'end'}
                fill="#101828"
                font-size="12"
                font-family="Avenir Next, PingFang SC, Microsoft YaHei, sans-serif"
              >
                {node.name} ({Number((node.value ?? 0)).toFixed(decimals)})
              </text>
            {/each}
          </g>
        </svg>
      {:else}
        <p class="small">导入文件并点击“生成图表”后，这里会显示桑基图预览。</p>
      {/if}
    </div>
  </div>
</main>
