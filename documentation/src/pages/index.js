/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

import React from 'react';
import classnames from 'classnames';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import withBaseUrl from '@docusaurus/withBaseUrl';
import styles from './styles.module.css';

const features = [
  {
    title: <>Integrations</>,
    Url: "/docs/categories/integrations",
    description: (<></>),
  },
  {
    title: <>Plugins</>,
    Url: "/docs/categories/plugins",
    description: (<></>),
  },
  {
    title: <>AppDaemon Apps</>,
    Url: "/docs/categories/appdaemon_apps",
    description: (<></>),
  },
  {
    title: <>Python Scripts</>,
    Url: "/docs/categories/python_scripts",
    description: (<></>),
  },
  {
    title: <>Themes</>,
    Url: "/docs/categories/themes",
    description: (<></>),
  },
];

function Home() {
  const context = useDocusaurusContext();
  const { siteConfig = {} } = context;
  return (
    <Layout title={`${siteConfig.title}`}>
      <header className={classnames('hero hero--primary', styles.heroBanner)}>
        <div className="container">
          <h1 className="hero__title">{siteConfig.title}</h1>
          <p className="hero__subtitle">{siteConfig.tagline}</p>
          <p className="hero__subtitle">HACS gives you a powerful UI to handle downloads of custom needs.</p>
          <div className={styles.buttons}>
            <Link
              className={classnames(
                'button button--outline button--secondary button--lg btt',
                styles.getStarted,
              )}
              to={withBaseUrl('docs/installation/prerequisites')}>
              Installation
            </Link>
            <Link
              className={classnames(
                'button button--outline button--secondary button--lg btt',
                styles.getStarted,
              )}
              to={withBaseUrl('docs/configuration/start')}>
              Configuration
            </Link>
            <Link
              className={classnames(
                'button button--outline button--secondary button--lg btt',
                styles.getStarted,
              )}
              to={withBaseUrl('docs/basic/getting_started')}>
              Usage
            </Link>
          </div>
        </div>
      </header>
      <main>
        {features && features.length && (
          <section className={styles.features}>
            <div className="container">
              <div className="row">
                {features.map(({ Url, title, description }, idx) => (

                  <div
                    key={idx}
                    className={classnames('col col--4', styles.feature)}>
                    <a href={Url}><h3>{title}</h3></a>
                    <p>{description}</p>
                  </div>

                ))}
              </div>
            </div>
          </section>
        )}
        <section className={classnames('hero hero--primary', styles.heroBanner)}>
          <div className="container">
            <img src="img/hacsdemo.gif"></img>
          </div>
        </section>
      </main>
    </Layout>
  );
}

export default Home;
