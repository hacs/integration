export default {
  "plugins": [],
  "themes": [],
  "customFields": {},
  "themeConfig": {
    "navbar": {
      "title": "HACS (Home Assistant Community Store)",
      "links": [
        {
          "to": "developer/start",
          "label": "Developer docs",
          "position": "left"
        },
        {
          "to": "help",
          "label": "Help",
          "position": "left"
        },
        {
          "href": "https://github.com/custom-components/hacs",
          "label": "GitHub",
          "position": "left"
        }
      ]
    },
    "scripts": [
      "https://buttons.github.io/buttons.js"
    ],
    "presets": [
      [
        "@docusaurus/preset-classic",
        {
          "docs": {
            "editUrl": "https://github.com/custom-components/hacs/edit/master/documentation/docs/",
            "path": "./docs",
            "sidebarPath": "/workspaces/hacs/documentation/sidebars.json"
          }
        }
      ]
    ]
  },
  "title": "HACS (Home Assistant Community Store)",
  "baseUrl": "/",
  "url": "https://hacs.netlify.com",
  "tagline": "Home Assistant Community Store",
  "favicon": "",
  "githubHost": "github.com",
  "organizationName": "custom-components"
};