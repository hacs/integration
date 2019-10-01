/* eslint-disable no-console, no-undef, prefer-destructuring, prefer-destructuring, no-constant-condition, max-len */
import {
  LitElement,
  customElement,
  CSSResultArray,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";

import { HomeAssistant } from "custom-card-helpers";

import { load_lovelace } from "./misc/LoadLovelace";
import { navigate } from "./misc/navigate";

import { HacsStyle } from "./style/hacs-style";

import scrollToTarget from "./misc/ScrollToTarget";
import "./panels/corePanel";
import "./panels/settings";
import "./panels/repository";

import { Configuration, Repository, Route } from "./types";

@customElement("hacs-frontend")
class HacsFrontendBase extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repository[]

  @property()
  public configuration!: Configuration

  @property()
  public route!: Route;

  @property()
  public narrow!: boolean;

  @property()
  public panel!: string;

  @property()
  public repository: string;

  @property()
  public repository_view = false;

  private getRepositories(): void {
    this.hass.connection.sendMessagePromise({
      type: "hacs/config"
    }).then(
      (resp) => {
        this.configuration = (resp as Configuration);
      },
      (err) => {
        console.error('Message failed!', err);
      }
    );
    this.hass.connection.sendMessagePromise({
      type: "hacs/repositories"
    }).then(
      (resp) => {
        this.repositories = (resp as Repository[]);
      },
      (err) => {
        console.error('Message failed!', err);
      }
    );
    this.requestUpdate();
  }

  protected firstUpdated() {
    localStorage.setItem("hacs-search", "");
    this.panel = this._page;
    this.getRepositories();

    if (/repository\//i.test(this.panel)) {
      // How fun, this is a repository!
      this.repository_view = true;
      this.repository = this.panel.split("/")[1];
    } else this.repository_view = false;

    // "steal" LL elements
    load_lovelace();
  }

  protected render(): TemplateResult | void {
    // Handle access to root
    if (this.panel === "") {
      navigate(this, "/hacs/installed");
      this.panel = "installed";
    }

    if (this.repositories === undefined) return html`<paper-spinner active class="loader"></paper-spinner>`;

    if (/repository\//i.test(this.panel)) {
      this.repository_view = true;
      this.repository = this.panel.split("/")[1];
      this.panel = this.panel.split("/")[0];
    } else this.repository_view = false;

    const page = this.panel;

    return html`
    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
        <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize(`component.hacs.config.title`)}</div>
        </app-toolbar>
    <paper-tabs
    scrollable
    attr-for-selected="page-name"
    .selected=${page}
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

    ${(this.configuration.appdaemon
        ? html`<paper-tab page-name="appdaemon">
        ${this.hass.localize(`component.hacs.common.appdaemon_apps`)}
    </paper-tab>` : "")}

    ${(this.configuration.python_script
        ? html`<paper-tab page-name="python_script">
        ${this.hass.localize(`component.hacs.common.python_scripts`)}
    </paper-tab>` : "")}

    ${(this.configuration.theme
        ? html`<paper-tab page-name="theme">
        ${this.hass.localize(`component.hacs.common.themes`)}
    </paper-tab>` : "")}

    <paper-tab page-name="settings">
    ${this.hass.localize("component.hacs.common.settings")}
    </paper-tab>
    </paper-tabs>
    </app-header>

    ${(this.panel === "installed" || "repository" || "integration" || "plugin" || "appdaemon" || "python_script" || "theme" ? html`
    <hacs-panel
    .hass=${this.hass}
    .configuration=${this.configuration}
    .repositories=${this.repositories}
    .panel=${this.panel}
    .repository_view=${this.repository_view}
    .repository=${this.repository}
    >
    </hacs-panel>` : "")}

    ${(this.panel === "settings" ? html`
    <hacs-panel-settings
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-settings>` : "")}

    </app-header-layout>`;
  }

  handlePageSelected(ev) {
    this.repository_view = false;
    const newPage = ev.detail.item.getAttribute("page-name");
    this.panel = newPage;
    this.requestUpdate();
    if (newPage !== this._page) {
      navigate(this, `/hacs/${newPage}`);
    }

    scrollToTarget(
      this,
      // @ts-ignore
      this.shadowRoot!.querySelector("app-header-layout").header.scrollTarget
    );
  }

  private get _page() {
    if (this.route.path.substr(1) === null) return "installed";
    return this.route.path.substr(1);
  }

  static get styles(): CSSResultArray {
    return [HacsStyle, css`
    paper-spinner.loader {
      position: absolute;
      top: 20%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 99;
      width: 300px;
      height: 300px;
   }
    `];
  }
}
