class HacsOverviewCard extends HTMLElement {
  constructor() {
    super();
  }

  SetCSS() {
    return `
        :host {
            background: var(
              --ha-card-background,
              var(--paper-card-background-color, white)
            );
            border-radius: var(--ha-card-border-radius, 2px);
            box-shadow: var(
              --ha-card-box-shadow,
              0 2px 2px 0 rgba(0, 0, 0, 0.14),
              0 1px 5px 0 rgba(0, 0, 0, 0.12),
              0 3px 1px -2px rgba(0, 0, 0, 0.2)
            );
            color: var(--primary-text-color);
            display: block;
            transition: all 0.3s ease-out;
            position: relative;
          }
          .card-header,
          :host ::slotted(.card-header) {
            color: var(--ha-card-header-color, --primary-text-color);
            font-family: var(--ha-card-header-font-family, inherit);
            font-size: var(--ha-card-header-font-size, 24px);
            letter-spacing: -0.012em;
            line-height: 32px;
            padding: 24px 16px 16px;
            display: block;
          }
          :host ::slotted(.card-content:not(:first-child)),
          slot:not(:first-child)::slotted(.card-content) {
            padding-top: 0px;
            margin-top: -8px;
          }
          :host ::slotted(.card-content) {
            padding: 16px;
          }
          :host ::slotted(.card-actions) {
            border-top: 1px solid #e8e8e8;
            padding: 5px 16px;
          }
        `;
  }

  connectedCallback() {
    var computedHTML = ``;
    computedHTML += `<style>${this.SetCSS()}</style>`;

    if (this.getAttribute("icon")) {
      computedHTML += `<i class='fas fa-cube'></i>`;
    }

    if (this.getAttribute("header")) {
      computedHTML += `<div class="card-header">${this.getAttribute("header")}</div>`;
    }

    computedHTML += `<slot></slot>`;

    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = computedHTML;

  }
}

customElements.define('hacs-overview-card', HacsOverviewCard);