(function () {
  'use strict'

  const data = JSON.parse(
    document.getElementById('django-launch-editor-data').textContent
  )

  async function openInEditor (button, status, token) {
    button.disabled = true
    status.className = 'django-launch-editor-status'
    status.textContent = 'Opening…'

    const body = new FormData()
    body.append('token', token)
    let error = null
    try {
      const response = await fetch(data.url, {
        method: 'POST',
        body,
        mode: 'same-origin',
        credentials: 'same-origin'
      })
      const contentType = response.headers.get('Content-Type') ?? ''
      const json = contentType.startsWith('application/json')
        ? await response.json()
        : {}
      if (response.status === 200 && typeof json.location === 'string') {
        // No editor was found, so the location to copy was sent instead.
        showLocation(json)
      } else if (response.status !== 204) {
        if (typeof json.error === 'string') {
          error = json.error
        } else if (response.redirected) {
          error = `Request was redirected to ${response.url}.`
        } else {
          error = `Request failed with status ${response.status}.`
        }
      }
    } catch (exc) {
      error = `Request failed: ${exc.message}`
    }

    button.disabled = false
    if (error === null) {
      status.textContent = ''
    } else {
      status.classList.add('error')
      status.textContent = error
    }
  }

  const COPY_ICON =
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>' +
    '<rect width="13" height="13" x="9" y="9" rx="2"/>' +
    '</svg>'

  let dialog = null

  function getDialog () {
    if (dialog === null) {
      dialog = document.createElement('dialog')
      dialog.className = 'django-launch-editor-dialog'
      dialog.setAttribute('closedby', 'any')
      dialog.setAttribute('aria-labelledby', 'django-launch-editor-title')

      const title = document.createElement('h2')
      title.id = 'django-launch-editor-title'
      title.textContent = 'Running editor not detected'

      const copyButton = document.createElement('button')
      copyButton.type = 'button'
      copyButton.className = 'django-launch-editor-copy'
      copyButton.title = 'Copy to clipboard'
      copyButton.setAttribute('aria-label', 'Copy to clipboard')
      copyButton.innerHTML = COPY_ICON
      copyButton.addEventListener('click', async () => {
        const code = dialog.querySelector('code')
        // Called directly from the click, so browsers like Safari allow it.
        try {
          await navigator.clipboard.writeText(code.textContent)
        } catch {
          window.getSelection().selectAllChildren(code)
        }
      })

      const form = document.createElement('form')
      form.method = 'dialog'
      const button = document.createElement('button')
      button.textContent = 'OK'
      button.autofocus = true
      form.append(button)

      dialog.append(
        title,
        document.createElement('p'),
        copyButton,
        document.createElement('code'),
        form
      )
      document.body.append(dialog)
    }
    return dialog
  }

  async function showLocation ({ location, relative }) {
    let copied = false
    try {
      await navigator.clipboard.writeText(location)
      copied = true
    } catch {
      // The clipboard is unavailable, for example on an insecure origin.
    }

    const description = relative ? 'Relative path' : 'Path'
    const dialog = getDialog()
    dialog.querySelector('p').textContent = copied
      ? `${description} with line number copied to clipboard.`
      : `Copy the ${description.toLowerCase()} with line number:`
    const code = dialog.querySelector('code')
    code.textContent = location
    code.hidden = copied
    dialog.querySelector('.django-launch-editor-copy').hidden = copied
    dialog.showModal()
  }

  // Wrap the given nodes, such as the filename and line number, in a
  // button. Show the status after any text that follows, such as “, in view”.
  function addButton (nodes, token) {
    if (token === null) {
      return
    }

    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'django-launch-editor'
    button.title = 'Open in editor'
    nodes[0].before(button)
    button.append(...nodes)

    const status = document.createElement('span')
    status.className = 'django-launch-editor-status'
    status.setAttribute('role', 'status')
    const rest = button.nextSibling
    if (rest?.nodeType === Node.TEXT_NODE) {
      rest.textContent = rest.textContent.trimEnd()
      rest.after(' ', status)
    } else {
      button.after(' ', status)
    }

    button.addEventListener('click', (event) => {
      event.stopPropagation()
      openInEditor(button, status, token)
    })
  }

  // Return the filename element plus the following “, line 12” text.
  function filenameAndLine (element) {
    const text = element.nextSibling
    if (text?.nodeType === Node.TEXT_NODE) {
      const match = text.textContent.match(/^, line \d+/)
      if (match !== null) {
        text.splitText(match[0].length)
        return [element, text]
      }
    }
    return [element]
  }

  const frames = document.querySelectorAll('#browserTraceback li.frame')
  // Frames are matched up by position, so give up if Django’s template has
  // changed in a way that breaks that.
  if (frames.length === data.frames.length) {
    frames.forEach((frame, index) => {
      const fname = frame.querySelector(':scope > code.fname')
      if (fname !== null) {
        addButton(filenameAndLine(fname), data.frames[index])
      }
    })
    const fname = document.querySelector('#summary .fname')
    if (fname !== null && data.frames.length > 0) {
      addButton(filenameAndLine(fname), data.frames[data.frames.length - 1])
    }
  }

  // Template errors read “In template <code>name</code>, error at line
  // <strong>12</strong>”.
  const templateName = document.querySelector('#template p > code')
  if (templateName !== null) {
    const nodes = [templateName]
    const text = templateName.nextSibling
    const line = text?.nextSibling
    if (text?.nodeType === Node.TEXT_NODE && line?.nodeName === 'STRONG') {
      nodes.push(text, line)
    }
    addButton(nodes, data.template)
  }
})()
