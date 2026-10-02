import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { BrowserNoteMeasurement } from '../lib/andrea-browser-metrics';
import { AndreaResponseTimes } from './AndreaResponseTimes';

describe('response timing disclosure', () => {
  it('labels received content, DOM update and transport completion as distinct boundaries', () => {
    const m = new BrowserNoteMeasurement(() => 0); m.mode('brief_quotes'); m.content(); m.finish('success', true, 'stop'); m.commit(true, true);
    const html = renderToStaticMarkup(<AndreaResponseTimes times={m.snapshot()} />);
    expect(html).toContain('Risposta senza inferenza'); expect(html).toContain('Completata');
    expect(html).toContain('Primo contenuto ricevuto dal browser'); expect(html).toContain('Primo aggiornamento');
    expect(html).toContain('non il momento esatto'); expect(html).toContain('non vanno sommati');
    expect(html).toContain('non correlate'); expect(html).not.toContain('token/s');
  });
  it('shows interruption and background observation without calling the request completed', () => {
    const m = new BrowserNoteMeasurement(() => 0, false); m.finish('cancelled');
    const html = renderToStaticMarkup(<AndreaResponseTimes times={m.snapshot()} />);
    expect(html).toContain('Interrotta'); expect(html).toContain('secondo piano');
    expect(html).toContain('Non disponibile'); expect(html).not.toContain('Completata');
  });
});
