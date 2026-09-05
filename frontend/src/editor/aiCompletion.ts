/**
 * CodeMirror 6 AI 内联补全扩展（Copilot 风格 ghost text）
 *
 * - 停顿 delay 毫秒后自动请求补全，光标处显示灰色幽灵文本
 * - Tab 接受 / Esc 或继续输入拒绝
 * - enabled() 返回 false 时完全静默（对应工具栏开关）
 */

import { StateField, StateEffect, Prec } from '@codemirror/state'
import type { Extension } from '@codemirror/state'
import { EditorView, Decoration, WidgetType, keymap } from '@codemirror/view'
import type { DecorationSet } from '@codemirror/view'

interface GhostPayload {
  pos: number
  text: string
}

const setGhostText = StateEffect.define<GhostPayload | null>()

class GhostWidget extends WidgetType {
  constructor(readonly text: string) {
    super()
  }
  override eq(other: GhostWidget): boolean {
    return other.text === this.text
  }
  toDOM(): HTMLElement {
    const span = document.createElement('span')
    span.className = 'cm-ai-ghost'
    span.textContent = this.text
    span.title = 'Tab 接受 · Esc 拒绝'
    return span
  }
  override ignoreEvent(): boolean {
    return true
  }
}

interface GhostFieldValue {
  ghost: GhostPayload | null
  deco: DecorationSet
}

const ghostField = StateField.define<GhostFieldValue>({
  create: () => ({ ghost: null, deco: Decoration.none }),
  update(value, tr) {
    let ghost = value.ghost
    let deco = value.deco.map(tr.changes)

    for (const e of tr.effects) {
      if (e.is(setGhostText)) {
        ghost = e.value
        if (ghost) {
          const pos = Math.min(ghost.pos, tr.state.doc.length)
          deco = Decoration.set([
            Decoration.widget({ widget: new GhostWidget(ghost.text), side: 1 }).range(pos),
          ])
        } else {
          deco = Decoration.none
        }
      }
    }

    // 用户继续输入/移动光标导致文档变化且本事务没有新 ghost → 清除旧 ghost
    if (!tr.changes.empty && !tr.effects.some(e => e.is(setGhostText))) {
      ghost = null
      deco = Decoration.none
    }
    return { ghost, deco }
  },
  provide: f => EditorView.decorations.from(f, v => v.deco),
})

function getGhost(view: EditorView): GhostPayload | null {
  return view.state.field(ghostField).ghost
}

const acceptKeymap = Prec.highest(
  keymap.of([
    {
      key: 'Tab',
      run: view => {
        const ghost = getGhost(view)
        if (!ghost) return false
        const pos = Math.min(ghost.pos, view.state.doc.length)
        view.dispatch({
          changes: { from: pos, insert: ghost.text },
          selection: { anchor: pos + ghost.text.length },
          effects: setGhostText.of(null),
        })
        return true
      },
    },
    {
      key: 'Escape',
      run: view => {
        if (!getGhost(view)) return false
        view.dispatch({ effects: setGhostText.of(null) })
        return true
      },
    },
  ]),
)

export interface AICompletionOptions {
  /** 是否启用（React 开关通过 ref 传入） */
  enabled: () => boolean
  /** 请求补全：传入完整代码与光标位置，返回建议文本（空串 = 无建议） */
  fetchCompletion: (code: string, line: number, col: number) => Promise<string>
  /** 停顿多少毫秒后触发，默认 900 */
  delay?: number
}

export function aiCompletion(opts: AICompletionOptions): Extension {
  const delay = opts.delay ?? 900

  const plugin = EditorView.updateListener.of(update => {
    if (!opts.enabled()) return
    if (!update.docChanged && !update.selectionSet) return

    const view = update.view
    const mySeq = ++seq
    if (timer) window.clearTimeout(timer)

    timer = window.setTimeout(async () => {
      if (!opts.enabled()) return
      const pos = view.state.selection.main.head
      const line = view.state.doc.lineAt(pos)
      const code = view.state.doc.toString()
      if (!code.trim()) return
      try {
        const text = await opts.fetchCompletion(code, line.number, pos - line.from)
        // 期间文档或光标已变 → 丢弃过期结果
        if (mySeq !== seq) return
        if (!text.trim()) return
        const curPos = view.state.selection.main.head
        if (curPos !== pos) return
        view.dispatch({ effects: setGhostText.of({ pos, text }) })
      } catch {
        // 补全失败静默
      }
    }, delay)
  })

  let timer: number | undefined
  let seq = 0

  return [ghostField, acceptKeymap, plugin]
}
