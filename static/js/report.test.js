/**
 * Tests for static/js/report.js
 *
 * report.js is a plain (non-module) script that attaches jQuery handlers
 * as soon as it is loaded. Because it has no `module.exports`, we can't
 * import its functions directly — we drive it the same way a browser
 * would: build the DOM it expects, `require()` the script so it wires
 * itself up, then interact via clicks/changes and assert on the
 * resulting DOM state.
 *
 * Two non-obvious things this suite has to account for:
 *
 * 1. jQuery 4's `$(document).ready()` ALWAYS defers to a `setTimeout`,
 *    even when `document.readyState` is already "complete". A fixed
 *    delay to wait this out is flaky (a cold first run can take
 *    longer than a short guess), so instead we register our own
 *    `$(document).ready(resolve)` right after loading the script —
 *    jQuery fires ready callbacks in registration order, so our
 *    resolve is guaranteed to run right after report.js's own ready
 *    block, with no arbitrary timing involved.
 *
 * 2. `openTab()` (the function that adds the `active` class to a nav
 *    tab) is never actually bound to a click handler inside report.js
 *    itself — that wiring lives in the Django template (inline
 *    `onclick="openTab(...)"`). `validateForm`'s tab.click() calls are
 *    therefore inert here, and the only observable effect of picking
 *    a tab is the *focus* that happens ~50ms later (via a real
 *    `setTimeout` inside `focus_and_switch`). Rather than guess that
 *    delay too, `waitForFocus()` below polls until the expected
 *    element is actually focused (or times out), so it isn't
 *    sensitive to machine speed either.
 */

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Resolves once jQuery's ready queue has actually run report.js's ready block. */
function waitForJQueryReady() {
  return new Promise((resolve) => {
    $(document).ready(resolve);
  });
}

/** Polls a condition instead of guessing a fixed delay; throws on timeout. */
async function waitUntil(conditionFn, { timeout = 1000, interval = 5 } = {}) {
  const start = Date.now();
  while (!conditionFn()) {
    if (Date.now() - start > timeout) {
      throw new Error('waitUntil: condition was not met within the timeout');
    }
    await sleep(interval);
  }
}

/** Waits until `element` is document.activeElement (focus_and_switch's 50ms setTimeout). */
function waitForFocus(element) {
  return waitUntil(() => document.activeElement === element, { timeout: 500 });
}

function buildFixture() {
  document.body.innerHTML = `
    <form id="report">
      <ul>
        <li id="nav_Administrative" class="tab_links active"></li>
        <li id="nav_Quantitative" class="tab_links"></li>
        <li id="nav_Strategic" class="tab_links"></li>
        <li id="nav_Learning" class="tab_links"></li>
      </ul>

      <div id="Administrative" class="tab_content">
        <select id="activity_associated">
          <option value="" data-poa_area="" selected>--</option>
          <option value="1" data-poa_area="1">Strategic activity</option>
          <option value="2" data-poa_area="0">Non-strategic activity</option>
        </select>
        <input id="area_responsible" type="text" />
        <input id="initial_date" type="text" />
        <textarea id="description"></textarea>
        <input id="links" type="text" />
        <select id="funding_associated" multiple></select>
        <select id="partners_activated" class="select-with-text" multiple></select>
      </div>

      <div id="Quantitative" class="tab_content">
        <div id="metrics_to_select">
          <fieldset id="metrics_fieldset">
            <input type="checkbox" name="metrics_related" value="10" />
            <input type="checkbox" name="metrics_related" value="11" />
          </fieldset>
        </div>
      </div>

      <div id="Strategic" class="tab_content">
        <fieldset id="directions_fieldset">
          <input type="checkbox" value="1" />
          <input type="checkbox" value="2" />
        </fieldset>
        <div id="next_strategic" class="invisible_field"></div>
      </div>

      <div id="Learning" class="tab_content">
        <fieldset id="strategic_questions_fieldset">
          <input type="checkbox" value="1" />
          <input type="checkbox" value="2" />
        </fieldset>
        <div id="learning_container">
          <textarea id="learning"></textarea>
        </div>
      </div>

      <div class="operation-header">Header A</div>
      <div class="operation-header">Header A</div>
      <div class="operation-header">Header B</div>

      <input type="checkbox" class="toggle__input wiki" id="extra_field" checked />
      <div class="extra_field invisible_field"></div>

      <button id="submit_report" type="button"></button>
      <button id="nav_submit_report" type="button"></button>
      <button id="submit_report_from_quantitative" type="button" class="invisible_field"></button>
    </form>
  `;
}

/**
 * (Re)loads report.js against a freshly built DOM and fresh globals,
 * then waits one real tick so jQuery's deferred ready callback (and
 * everything inside it) has already run by the time this resolves.
 *
 * @param {string} [activityValue] optional value to pre-select on
 *   #activity_associated before the script runs, so ready-time code
 *   that reads it (show_metrics_options) sees it.
 */
async function loadReportScript(activityValue) {
  jest.resetModules();
  buildFixture();

  if (activityValue !== undefined) {
    document.getElementById('activity_associated').value = activityValue;
  }

  global.select_partners = 'Select partners';
  global.get_metrics_url = '/fake-metrics-url';
  global.report_id = 42;
  global.metrics_set = [7];

  global.$ = global.jQuery = require('jquery');

  // Stub select2 — it's a jQuery UI plugin, not part of jQuery core,
  // and isn't relevant to the logic under test.
  global.$.fn.select2 = jest.fn().mockReturnThis();

  // Never let $.ajax hit the network; each test controls the response
  // via the captured config object's success/error callbacks.
  global.$.ajax = jest.fn();

  // jsdom doesn't implement real form submission; stub it so we can
  // assert on it instead of getting a "not implemented" error.
  window.HTMLFormElement.prototype.submit = jest.fn();

  require('./report.js');

  // jQuery 4's ready handler always fires via a deferred setTimeout,
  // even though document.readyState is already "complete" here.
  // Waiting on our own ready callback (queued after report.js's own)
  // is deterministic — no arbitrary delay to guess.
  await waitForJQueryReady();
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe('toggle_field (via the ready-time checkbox scan)', () => {
  test('removes invisible_field from elements matching a checked toggle checkbox', async () => {
    await loadReportScript();
    // #extra_field checkbox starts checked, .extra_field starts with invisible_field
    expect(document.querySelector('.extra_field').classList.contains('invisible_field')).toBe(false);
  });
});

describe('hide_duplicate_headers', () => {
  test('hides repeated .operation-header elements but keeps the first of each text', async () => {
    await loadReportScript();
    const headers = document.querySelectorAll('.operation-header');
    expect(headers[0].style.display).not.toBe('none'); // first "Header A" stays
    expect(headers[1].style.display).toBe('none');      // duplicate "Header A" hidden
    expect(headers[2].style.display).not.toBe('none');  // "Header B" is unique, stays
  });
});

describe('toggle_tab', () => {
  test('hides Strategic/Learning nav and shows the quantitative submit button when activity has no poa_area', async () => {
    await loadReportScript();
    $('#activity_associated').val('2').trigger('change');

    expect(document.getElementById('nav_Strategic').style.display).toBe('none');
    expect(document.getElementById('nav_Learning').style.display).toBe('none');
    expect(document.getElementById('next_strategic').classList.contains('invisible_field')).toBe(true);
    expect(document.getElementById('submit_report_from_quantitative').classList.contains('invisible_field')).toBe(false);
  });

  test('shows Strategic/Learning nav and hides the quantitative submit button when activity has a poa_area', async () => {
    await loadReportScript();
    $('#activity_associated').val('1').trigger('change');

    expect(document.getElementById('nav_Strategic').style.display).toBe('block');
    expect(document.getElementById('nav_Learning').style.display).toBe('block');
    expect(document.getElementById('next_strategic').classList.contains('invisible_field')).toBe(false);
    expect(document.getElementById('submit_report_from_quantitative').classList.contains('invisible_field')).toBe(true);
  });

  test('does nothing when the selected option has no data-poa_area at all', async () => {
    await loadReportScript();
    // The default selected option's data-poa_area is "" (empty string),
    // which the guard clause treats the same as undefined/null and
    // returns early — so nav_Strategic keeps its un-set inline style.
    expect(document.getElementById('nav_Strategic').style.display).toBe('');
  });
});

describe('show_metrics_options renders the fieldset from the ajax response', () => {
  test('requests metrics for the selected activity/report id', async () => {
    await loadReportScript('1');

    expect($.ajax).toHaveBeenCalledTimes(1);
    const ajaxCall = $.ajax.mock.calls[0][0];
    expect(ajaxCall.url).toBe('/fake-metrics-url');
    // jQuery's .val() on an empty <select multiple> with no options returns [].
    expect(ajaxCall.data).toEqual({ activity: '1', fundings: [], instance: 42 });
  });

  test('builds checkboxes/radios from the response and marks pre-selected metrics as checked', async () => {
    await loadReportScript('1');
    const ajaxCall = $.ajax.mock.calls[0][0];

    ajaxCall.success({
      main: true,
      objects: [
        {
          project: 'Project X',
          main: true,
          metrics: [{ id: 7, text: 'Metric seven' }],
        },
      ],
    });

    const fieldset = document.getElementById('metrics_fieldset');
    expect(fieldset).not.toBeNull();
    const input = fieldset.querySelector('input[value="7"]');
    expect(input.type).toBe('radio'); // projectEl.main === true => radio, not checkbox
    expect(input.checked).toBe(true); // 7 is in metrics_set

    expect($('#learning').data('has_learning')).toBe(true);
    expect(document.getElementById('learning_container').style.display).not.toBe('none');
  });

  test('hides the learning container when the response has no main metric', async () => {
    await loadReportScript('1');
    const ajaxCall = $.ajax.mock.calls[0][0];

    ajaxCall.success({ main: false, objects: [] });

    expect($('#learning').data('has_learning')).toBe(false);
    expect(document.getElementById('learning_container').style.display).toBe('none');
  });
});

describe('validateForm (via clicking #submit_report)', () => {
  test('blocks submission and focuses #activity_associated itself when nothing is filled', async () => {
    await loadReportScript();
    // #activity_associated is first in admin_fields, and its default
    // selected option has value="" — so it's the first missing field,
    // ahead of area_responsible/initial_date/description/links.
    $('#submit_report').trigger('click');
    await waitForFocus(document.getElementById('activity_associated'));

    expect(document.activeElement).toBe(document.getElementById('activity_associated'));
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('blocks submission and focuses the first empty admin field once activity is chosen', async () => {
    await loadReportScript('1');
    // area_responsible, initial_date, description, links are still empty in the fixture
    $('#submit_report').trigger('click');
    await waitForFocus(document.getElementById('area_responsible'));

    expect(document.activeElement).toBe(document.getElementById('area_responsible'));
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('blocks submission and focuses the first metric checkbox when none is checked', async () => {
    await loadReportScript('1');
    fillAdminFields();
    $('#submit_report').trigger('click');
    await waitForFocus(document.querySelector('#metrics_fieldset input[value="10"]'));

    expect(document.activeElement).toBe(
      document.querySelector('#metrics_fieldset input[value="10"]')
    );
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('submits immediately when activity is not strategic (poa_area !== 1), once admin+metric are filled', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '2'; // poa_area not 1
    checkOneMetric();

    $('#submit_report').trigger('click');

    expect(window.HTMLFormElement.prototype.submit).toHaveBeenCalledTimes(1);
  });

  test('blocks submission and focuses the first direction checkbox when none is checked (strategic activity)', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '1'; // poa_area === "1"
    checkOneMetric();

    $('#submit_report').trigger('click');
    await waitForFocus(document.querySelector('#directions_fieldset input[value="1"]'));

    expect(document.activeElement).toBe(
      document.querySelector('#directions_fieldset input[value="1"]')
    );
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('blocks submission and focuses the first strategic-question checkbox when none is checked', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '1';
    checkOneMetric();
    document.querySelector('#directions_fieldset input[value="1"]').checked = true;

    $('#submit_report').trigger('click');
    await waitForFocus(document.querySelector('#strategic_questions_fieldset input[value="1"]'));

    expect(document.activeElement).toBe(
      document.querySelector('#strategic_questions_fieldset input[value="1"]')
    );
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('submits when admin, metric, direction, and strategic question are all filled and there is no learning requirement', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '1';
    checkOneMetric();
    document.querySelector('#directions_fieldset input[value="1"]').checked = true;
    document.querySelector('#strategic_questions_fieldset input[value="1"]').checked = true;
    // $('#learning').data('has_learning') is left unset (falsy) => the learning block is skipped

    $('#submit_report').trigger('click');

    expect(window.HTMLFormElement.prototype.submit).toHaveBeenCalledTimes(1);
  });

  test('blocks submission and focuses #learning when learning is required but the text is under 500 characters', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '1';
    checkOneMetric();
    document.querySelector('#directions_fieldset input[value="1"]').checked = true;
    document.querySelector('#strategic_questions_fieldset input[value="1"]').checked = true;
    $('#learning').data('has_learning', true);
    $('#learning').val('too short');

    // This branch focuses synchronously (no setTimeout involved).
    $('#submit_report').trigger('click');

    expect(document.activeElement).toBe(document.getElementById('learning'));
    expect(window.HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
  });

  test('submits when learning is required and the text is 500+ characters', async () => {
    await loadReportScript();
    fillAdminFields();
    document.querySelector('#activity_associated').value = '1';
    checkOneMetric();
    document.querySelector('#directions_fieldset input[value="1"]').checked = true;
    document.querySelector('#strategic_questions_fieldset input[value="1"]').checked = true;
    $('#learning').data('has_learning', true);
    $('#learning').val('x'.repeat(500));

    $('#submit_report').trigger('click');

    expect(window.HTMLFormElement.prototype.submit).toHaveBeenCalledTimes(1);
  });
});

function fillAdminFields() {
  document.getElementById('area_responsible').value = 'Someone';
  document.getElementById('initial_date').value = '2026-01-01';
  document.getElementById('description').value = 'Some description';
  document.getElementById('links').value = 'https://example.org';
}

function checkOneMetric() {
  document.querySelector('#metrics_fieldset input[value="10"]').checked = true;
}