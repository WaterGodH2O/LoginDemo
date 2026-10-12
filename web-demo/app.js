const snippets = {
  html: `<!-- index.html：结构。浏览器把它解析成 DOM -->
<article id="mini-page">
  <h2 id="mini-title">你好</h2>
  <p id="mini-text">这是写在 HTML 里的一段话。</p>
  <ul id="mini-list">
    <li>第一项</li>
  </ul>
</article>`,
  css: `/* style.css：外观。关掉「应用 CSS」就能看到素颜结构 */
.mini-page h2 {
  color: #9a3412;
}
body {
  background: #f3eee4;
}`,
  js: `// app.js：行为。找到节点，改的是 DOM，不是磁盘上的 html 文件
const title = document.querySelector('#mini-title')
title.textContent = '被脚本改过了'`,
}

const pipelineNotes = [
  '浏览器向服务器（或本地文件）请求 HTML。你现在打开的就是 index.html。',
  '解析器一边读标签一边搭 DOM 树。每个标签变成一个可以查询、修改的对象。',
  '遇到 <link> 下载 CSS，遇到 <script> 下载并执行 JS。本页脚本在 </body> 前，此时 DOM 已就绪。',
  'DOM + CSS 规则合成渲染树：看不见的节点（display:none）不会进入这一层。',
  'Layout（排版）：计算每个盒子的坐标和宽高。JS 改尺寸时可能再次触发这一步。',
  'Paint（绘制）：把颜色、文字、边框变成像素。你看见的屏幕是 DOM 的投影。',
]

const roleSnippet = document.querySelector('#role-snippet')
const jsLog = document.querySelector('#js-log')
const treeEl = document.querySelector('#dom-tree')
const miniPage = document.querySelector('#mini-page')
const miniTitle = document.querySelector('#mini-title')
const miniText = document.querySelector('#mini-text')
const miniList = document.querySelector('#mini-list')
const pipelineNote = document.querySelector('#pipeline-note')
const eventLog = document.querySelector('#event-log')
const stopBubble = document.querySelector('#stop-bubble')

let itemCount = 1
let currentStep = 0
let playTimer = null

function logJs(line) {
  const time = new Date().toLocaleTimeString()
  jsLog.textContent += `[${time}] ${line}\n`
  jsLog.scrollTop = jsLog.scrollHeight
}

function setRole(role) {
  document.querySelectorAll('.role-card').forEach((card) => {
    card.classList.toggle('is-active', card.dataset.role === role)
  })
  roleSnippet.textContent = snippets[role]
}

function setPipelineStep(index, playing) {
  currentStep = index
  document.querySelectorAll('.pipe-step').forEach((step) => {
    const n = Number(step.dataset.step)
    step.classList.toggle('is-current', n === index)
    step.classList.toggle('is-done', n < index)
  })
  pipelineNote.textContent = pipelineNotes[index]
  if (playing) {
    logJs(`// 渲染阶段 ${index + 1}: ${pipelineNotes[index]}`)
  }
}

function playPipeline() {
  clearInterval(playTimer)
  setPipelineStep(0, true)
  let i = 0
  playTimer = setInterval(() => {
    i += 1
    if (i >= pipelineNotes.length) {
      clearInterval(playTimer)
      return
    }
    setPipelineStep(i, true)
  }, 900)
}

function renderTree(flashHint) {
  const lines = []

  function walk(node, depth) {
    if (node.nodeType !== 1) return
    const id = node.id ? `#${node.id}` : ''
    const extra = node.children.length === 0 && node.textContent.trim()
      ? `  "${node.textContent.trim().slice(0, 18)}"`
      : ''
    const tag = `<${node.tagName.toLowerCase()}${id}>${extra}`
    const mark = flashHint && (node.id === flashHint || node.tagName.toLowerCase() === flashHint)
    lines.push(`${'  '.repeat(depth)}${mark ? '★ ' : ''}${tag}`)
    Array.from(node.children).forEach((child) => walk(child, depth + 1))
  }

  lines.push('article#mini-page')
  Array.from(miniPage.children).forEach((child) => walk(child, 1))
  treeEl.textContent = lines.join('\n')
}

function flashMini() {
  miniPage.style.background = '#fff6d6'
  setTimeout(() => {
    miniPage.style.background = ''
  }, 350)
}

document.querySelectorAll('.role-card').forEach((card) => {
  card.addEventListener('click', () => setRole(card.dataset.role))
})

document.querySelectorAll('.pipe-step').forEach((step) => {
  step.addEventListener('click', () => {
    clearInterval(playTimer)
    setPipelineStep(Number(step.dataset.step), false)
  })
})

document.querySelector('#play-pipeline').addEventListener('click', playPipeline)
document.querySelector('#reset-pipeline').addEventListener('click', () => {
  clearInterval(playTimer)
  setPipelineStep(0, false)
})

document.querySelector('#css-toggle').addEventListener('change', (event) => {
  miniPage.classList.toggle('is-unstyled', !event.target.checked)
  logJs(`miniPage.classList.toggle('is-unstyled', ${!event.target.checked})`)
})

document.querySelector('#btn-text').addEventListener('click', () => {
  miniTitle.textContent = '被脚本改过了'
  logJs("document.querySelector('#mini-title').textContent = '被脚本改过了'")
  renderTree('mini-title')
  flashMini()
})

document.querySelector('#btn-color').addEventListener('click', () => {
  const next = miniTitle.style.color === 'rgb(29, 78, 216)' ? '#9a3412' : '#1d4ed8'
  miniTitle.style.color = next
  logJs(`document.querySelector('#mini-title').style.color = '${next}'`)
  renderTree('mini-title')
  flashMini()
})

document.querySelector('#btn-add').addEventListener('click', () => {
  itemCount += 1
  const li = document.createElement('li')
  li.textContent = `第${itemCount}项（JS 动态创建）`
  miniList.appendChild(li)
  logJs("miniList.appendChild(document.createElement('li'))")
  renderTree('li')
  flashMini()
})

document.querySelector('#btn-remove').addEventListener('click', () => {
  const last = miniList.lastElementChild
  if (!last) return
  last.remove()
  logJs('miniList.lastElementChild.remove()')
  renderTree('mini-list')
  flashMini()
})

document.querySelector('#btn-delay').addEventListener('click', () => {
  logJs("setTimeout(() => { miniText.textContent = '...' }, 1000)")
  miniText.textContent = '（等 1 秒…）'
  renderTree('mini-text')
  setTimeout(() => {
    miniText.textContent = '定时器到了：JS 也可以稍后改 DOM。'
    logJs("miniText.textContent = '定时器到了：JS 也可以稍后改 DOM。'")
    renderTree('mini-text')
    flashMini()
  }, 1000)
})

document.querySelector('#btn-fetch').addEventListener('click', async () => {
  logJs("const res = await fetch('data.json')")
  miniText.textContent = '正在请求 data.json…'
  renderTree('mini-text')
  try {
    const res = await fetch('data.json')
    const data = await res.json()
    miniText.textContent = data.message
    logJs('miniText.textContent = data.message  // 网络数据写回 DOM')
  } catch (error) {
    miniText.textContent = '加载失败：请用本地服务器打开本页（不要直接双击文件）。'
    logJs('fetch 失败：file:// 下常被浏览器拦住跨源请求')
  }
  renderTree('mini-text')
  flashMini()
})

function bindBubble(id, label) {
  const el = document.querySelector(id)
  el.addEventListener('click', (event) => {
    if (id === '#bubble-inner' && stopBubble.checked) {
      event.stopPropagation()
      logJs("event.stopPropagation()  // 内层拦住，不再向外传")
    }
    const item = document.createElement('li')
    item.textContent = `${label} 收到 click`
    eventLog.appendChild(item)
    el.classList.remove('is-hit')
    void el.offsetWidth
    el.classList.add('is-hit')
    logJs(`// ${label} 的 click 监听器被调用`)
  })
}

document.querySelector('#bubble-outer').addEventListener('click', () => {
  eventLog.replaceChildren()
}, true)

bindBubble('#bubble-inner', '内层')
bindBubble('#bubble-middle', '中层')
bindBubble('#bubble-outer', '外层')

setRole('html')
setPipelineStep(0, false)
renderTree()
logJs('// 页面解析完成，app.js 开始执行')
logJs("const miniPage = document.querySelector('#mini-page')")
