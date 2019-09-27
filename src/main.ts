import {
  LitElement,
  customElement,
  CSSResult,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";

import {
  HomeAssistant
} from "custom-card-helpers";

import { load_lovelace } from "./FromCardTools"
import { navigate } from "./navigate"

import "./HacsSpinner"

import "./panels/installed";
import "./panels/store";
import "./panels/settings";
import "./panels/repository";

import { Configuration, Repositories, Route } from "./types"

@customElement("hacs-frontend")
class HacsFrontendBase extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories

  @property()
  public configuration!: Configuration

  @property()
  public route!: Route;

  @property()
  public narrow!: boolean;

  @property()
  public panel!: string;

  @property()
  public repository_view = false;

  private getRepositories(): void {
    this.hass.connection.sendMessagePromise({
      type: "hacs/config"
    }).then(
      (resp) => {
        this.configuration = resp;
      },
      (err) => {
        console.error('Message failed!', err);
      }
    )
    this.hass.connection.sendMessagePromise({
      type: "hacs/repositories"
    }).then(
      (resp) => {
        this.repositories = resp;
      },
      (err) => {
        console.error('Message failed!', err);
      }
    )
    this.requestUpdate();
  };

  firstUpdated() {
    this.panel = this._page;
    this.getRepositories()

    this.addEventListener("location-changed", async (e) => {
      console.log(e);
      console.log(await this.requestUpdate());
    });

    // "steal" LL elements
    load_lovelace()
  }

  protected render(): TemplateResult | void {
    // Handle access to root
    if (this.panel === "") {
      navigate(this, "/hacs/installed");
      this.panel = "installed";
    }

    console.log(this.panel)
    if (this.repositories === undefined) return html`<hacs-spinner></hacs-spinner>`;

    if (/repository\//i.test(this.panel)) {
      // How fun, this is a repository!
      this.repository_view = true
      var repository = this.panel.split("/")[1]
    }




    return html`
    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
      <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize(`component.hacs.config.title`)}</div>
      </app-toolbar>
    </app-header>
    <paper-tabs
    scrollable
    attr-for-selected="page-name"
    .selected="${this.panel}"
    @iron-activate=${this.handlePageSelected}>

    <paper-tab page-name="installed">
    ${this.hass.localize(`component.hacs.common.installed`)}
    </paper-tab>

    <paper-tab page-name="integration">
    ${this.hass.localize(`component.hacs.common.integrations`)}
    </paper-tab>

    <paper-tab page-name="plugin">
    ${this.hass.localize(`component.hacs.common.plugins`)}
    </paper-tab>

    ${(this.configuration.appdaemon ?
        html`<paper-tab page-name="appdaemon">
        ${this.hass.localize(`component.hacs.common.appdaemon_apps`)}
    </paper-tab>`: "")}

    ${(this.configuration.python_script ?
        html`<paper-tab page-name="python_script">
        ${this.hass.localize(`component.hacs.common.python_scripts`)}
    </paper-tab>`: "")}

    ${(this.configuration.theme ?
        html`<paper-tab page-name="theme">
        ${this.hass.localize(`component.hacs.common.themes`)}
    </paper-tab>`: "")}

    <paper-tab class="right" page-name="settings">
    ${this.hass.localize("component.hacs.common.settings")}
    </paper-tab>

    </paper-tabs>

    ${(this.repository_view ? html`
    <hacs-panel-repository
    .hass=${this.hass}
    .configuration=${this.configuration}
    .repositories=${this.repositories}
    .repository=${repository}>
    </hacs-panel-repository>` : "")}

    ${(this.panel === "installed" ? html`
      <hacs-panel-installed
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-installed>` : "")}

    ${(this.panel === "integration" || "plugin" || "appdaemon" || "python_script" || "theme" ? html`
    <hacs-panel-store
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .panel=${this.panel}
      .repository_view=${this.repository_view}>
      </hacs-panel-store>` : "")}

    ${(this.panel === "settings" ? html`
      <hacs-panel-settings
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-settings>` : "")}

    </app-header-layout>`
  }

  handlePageSelected(ev) {
    this.repository_view = false;
    const newPage = ev.detail.item.getAttribute("page-name");
    this.panel = newPage;
    navigate(this, `/hacs/${newPage}`);
    this.requestUpdate();
  }

  private get _page() {
    if (this.route.path.substr(1) === null) return "installed";
    return this.route.path.substr(1);
  }

  static get styles(): CSSResult {
    return css`
    :host {
      font-family: var(--paper-font-body1_-_font-family); -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing); font-size: var(--paper-font-body1_-_font-size); font-weight: var(--paper-font-body1_-_font-weight); line-height: var(--paper-font-body1_-_line-height);
    }

    app-header-layout, ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar, paper-tabs {
      background-color: var(--primary-color);
        font-weight: 400;
        text-transform: uppercase;
        color: var(--text-primary-color, white);
    }

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    h1 {
      font-family: var(--paper-font-title_-_font-family); -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing); white-space: var(--paper-font-title_-_white-space); overflow: var(--paper-font-title_-_overflow); text-overflow: var(--paper-font-title_-_text-overflow); font-size: var(--paper-font-title_-_font-size); font-weight: var(--paper-font-title_-_font-weight); line-height: var(--paper-font-title_-_line-height);
    }

    button.link {
      background: none;
        color: inherit;
        border: none;
        padding: 0;
        font: inherit;
        text-align: left;
        text-decoration: underline;
        cursor: pointer;
    }

    .card-actions a {
      text-decoration: none;
    }

    .card-actions .warning {
      --mdc-theme-primary: var(--google-red-500);
    }

    .card-group {
      margin-top: 24px;
    }

    .card-group .title {
      color: var(--primary-text-color);
        font-size: 1.5em;
        padding-left: 8px;
        margin-bottom: 8px;
    }

    .card-group .description {
      font-size: 0.5em;
        font-weight: 500;
        margin-top: 4px;
    }

    .card-group paper-card {
      --card-group-columns: 4;
        width: calc(
          (100% - 12px * var(--card-group-columns)) / var(--card-group-columns)
        );
        margin: 4px;
        vertical-align: top;
        height: 144px;
    }

    @media screen and (max-width: 1200px) and (min-width: 901px) {
    .card-group paper-card {
      --card-group-columns: 3;
    }

    }

    @media screen and (max-width: 900px) and (min-width: 601px) {
    .card-group paper-card {
      --card-group-columns: 2;
    }

    }

    @media screen and (max-width: 600px) and (min-width: 0) {
    .card-group paper-card {
      width: 100%;
          margin: 4px 0;
    }

    .content {
      padding: 0;
    }

    }

    ha-call-api-button {
      font-weight: 500;
        color: var(--primary-color);
    }

    .error {
      color: var(--google-red-500);
        margin-top: 16px;
    }

    paper-card {
      cursor: pointer;
    }
    ha-icon {
      margin-right: 16px;
      float: left;
      color: var(--primary-text-color);
    }
    ha-icon.update {
      color: var(--paper-orange-400);
    }
    ha-icon.running,
    ha-icon.installed {
      color: var(--paper-green-400);
    }
    ha-icon.hassupdate,
    ha-icon.snapshot {
      color: var(--paper-item-icon-color);
    }
    ha-icon.not_available {
      color: var(--google-red-500);
    }
    .title {
      margin-bottom: 16px;
      padding-top: 4px;
      color: var(--primary-text-color);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .addition {
      color: var(--secondary-text-color);
      position: relative;
      height: 2.4em;
      line-height: 1.2em;
    }
    ha-relative-time {
      display: block;
    }
    `;
  }
}