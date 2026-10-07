"""Read numeric phases of the latest retained structured request; no inference."""
import json
import math
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

URL = 'http://127.0.0.1:8008/api/andrea/metrics'
LIMIT = 2 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect non consentito per le misure locali.')


def number(value):
    return (value if type(value) in (int, float) and math.isfinite(value)
            and 0 <= value <= 2**53-1 else None)


def summary(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('records'), list):
        raise ValueError('Risposta delle misure non valida.')
    selected = next((record for record in reversed(snapshot['records'])
                     if isinstance(record, dict) and record.get('kind') == 'notes'
                     and record.get('inferenceUsed') is True
                     and 'structuredGenerationMs' in record), None)
    if selected is None:
        raise ValueError('Nessuna sintesi strutturata nelle misure in memoria. Esegui una sola sintesi della nota scelta dopo il riavvio.')
    native = selected.get('ollamaNative')
    native = native if isinstance(native, dict) else {}
    statuses = {'completed', 'cancelled', 'timeout', 'error', 'incomplete', 'truncated'}
    outcomes = {'accepted', 'rejected', 'abstained'}
    result = {
        'schema': 1, 'mode': 'production_native_phases_read_only',
        'selection': 'latest_retained_structured_notes_request',
        'inferencesIssuedByReader': 0, 'vaultReadByReader': False,
        'browserRendering': 'not_measured', 'qualityVerdict': 'not_assessed_by_reader',
        'transportStatus': selected.get('status') if selected.get('status') in statuses else None,
        'structuredOutcome': selected.get('structuredOutcome') if selected.get('structuredOutcome') in outcomes else None,
        'serverMs': {key: number(selected.get(key)) for key in (
            'retrievalMs', 'structuredFirstJsonMs', 'structuredGenerationMs',
            'structuredValidationMs', 'structuredAcceptedTextMs', 'firstTextMs', 'totalMs')},
        'native': {'source': 'ollama_terminal_frame', 'durationUnit': 'ms',
                   'terminalFrameReceived': native.get('terminalFrameReceived') is True,
                   **{key: number(native.get(key)) for key in (
                       'totalMs', 'loadMs', 'promptEvalMs', 'evalMs',
                       'promptEvalCount', 'promptEvalCachedCount', 'evalCount', 'evalTokensPerSecond')}},
    }
    return result


def read(opener=None):
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    request = Request(URL, headers={'Accept': 'application/json'}, method='GET')
    with opener.open(request, timeout=10) as response:
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Risposta delle misure troppo grande.')
    return summary(json.loads(raw))


if __name__ == '__main__':
    try:
        result = read()
    except (OSError, ValueError, TypeError) as exc:
        # Never print arbitrary server response bodies or exception contents.
        print('Lettura non riuscita: verifica OpenJarvis acceso sulla porta 8008 e una sintesi strutturata eseguita dopo il riavvio.')
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
