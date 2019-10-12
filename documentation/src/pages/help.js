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

function Helps(props) {
  const { config: siteConfig, language = '' } = props;
  const { baseUrl, docsUrl } = siteConfig;
  const docsPart = `${docsUrl ? `${docsUrl}/` : ''}`;
  const langPart = `${language ? `${language}/` : ''}`;
  const docUrl = doc => `${baseUrl}${docsPart}${langPart}${doc}`;

  const supportLinks = [
    {
      content: `Need to submitt a bug? [Before you do make sure you first have a look here.](${docUrl('issues.html')})`,
      title: 'Submitt issues',
    },
    {
      content: `Want to submit a Feature request? [Before you do make sure you first have a look here.](${docUrl('issues.html')})`,
      title: 'Add feature requests'
    },
  ];

  return (
    <div className="docMainWrapper wrapper">
      <Container className="mainContainer documentContainer postContainer">
        <div className="post">
          <header className="postHeader">
            <h1>Need help?</h1>
          </header>
          <GridBlock contents={supportLinks} layout="threeColumn" />
        </div>
      </Container>
    </div>
  );
}
const blocks = [
  {
    title: <>Browse Docs</>,
    description: (
      <>
        Learn more using the <a href="/">documentation on this site.</a>
      </>
    ),
  },
  {
    title: <>Join the community</>,
    description: (
      <>
        <a href="https://community.home-assistant.io/t/custom-component-hacs/121727" target="_blank">Ask questions about the documentation and project.</a>
      </>
    ),
  },
  {
    title: <>Stay up to date</>,
    description: (
      <>
        Find out what's new with this project over at <a href="https://github.com/custom-components/hacs" target="_blank">GitHub.</a>
      </>
    ),
  },
  {
    title: <>Need to submitt a bug?</>,
    description: (
      <>
        <a href="/docs/issues">Before you do make sure you first have a look here.</a>
      </>
    ),
  },
  {
    title: <>Want to submit a Feature request?</>,
    description: (
      <>
        <a href="/docs/issues">Before you do make sure you first have a look here.</a>
      </>
    ),
  },
];

function Help() {
  const context = useDocusaurusContext();
  return (
    <Layout title={`${siteConfig.title}: Help`}>
      <main>
        {blocks && blocks.length && (
          <section className={styles.blocks}>
            <div className="container">
              <div className="row">
                {blocks.map(({ title, description }, idx) => (
                  <div
                    key={idx}
                    className={classnames('col col--4', styles.feature)}>
                    <h3>{title}</h3>
                    <p>{description}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </main>
    </Layout>
  );
}

export default Help;
