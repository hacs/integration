import { LitElement, property, html } from 'lit-element';
import { routerMixin } from 'lit-element-router';

import "./panels/installed";
import "./panels/store";
import "./panels/settings";
import "./panels/repository";

import { Repositories, Configuration, Route } from "./types"
import { HomeAssistant } from "custom-card-helpers";

export class HacsRouter extends routerMixin(LitElement) {
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
    public repository: string;

    @property()
    public panel!: string;

    @property()
    public repository_view = false;

    static get routes() {
        return [{
            name: 'hacs-panel-settings',
            pattern: 'hacs/settings'
        }, {
            name: 'hacs-panel-store',
            pattern: 'hacs/integration'
        }, {
            name: 'hacs-panel-repository',
            pattern: 'hacs/repository/:id'
        }, {
            name: 'hacs-panel-installed',
            pattern: 'hacs/*'
        }];
    }

    render() {
        if (/repository\//i.test(this.panel)) {
            // How fun, this is a repository!
            this.repository_view = true
            this.repository = this.panel.split("/")[1]
        } else this.repository_view = false;
        return html`
            ${(this.repository_view ? html`
            <hacs-panel-repository
            .hass=${this.hass}
            .configuration=${this.configuration}
            .repositories=${this.repositories}
            .repository=${this.repository}>
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
            `
    }


    onRoute(route, params, query, data) {
        this.repository = params['id']
        console.log(route, params, query, data)
    }
}

customElements.define('hacs-router', HacsRouter)