export interface Route {
    path: string;
    prefix: string;
}

export interface Configuration {
    appdaemon?: boolean;
    country?: string;
    dev?: string;
    frontend_mode?: string;
    option_country?: string;
    python_script?: boolean;
    theme?: boolean;
}

interface Repository {
    category: string;
    country: string;
    description: string
    hide: boolean;
    id: string;
    installed: boolean;
    name: string;

}

export interface Repositories {
    content?: Repository[]
}