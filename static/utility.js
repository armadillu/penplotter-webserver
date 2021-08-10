// Nicer format for file list
function renderFileListElement(name) {

  const html = `<div class="uk-grid uk-grid-small">
            <div class="uk-width-expand">
              <a href="#" class="selectFile" data-filename="${name}">
                <span>${name}</span>
              </a>
            </div>
            <div class="uk-width-auto uk-text-right panel-icons">
              <a href="#" class="uk-icon-link deleteFile" data-filename="${name}" title="Delete" data-uk-tooltip data-uk-icon="icon: close"></a>
            </div>
          </div>`;

  return html;
}

// Simplift notification handling
function notify(message, status) {
    UIkit.notification({
      message: message,
      status: status,
      pos: 'top-right',
      timeout: 5000
  });
}
