$(document).ready(function () {
  $('.toggle__input.wiki').each(function () {
    if (this.checked) {
      toggle_field(this.id);
    }
  });

  show_metrics_options();

  $(".select-with-text").not("#partners_activated").select2();

  $('#partners_activated').select2({
    tags: true,
    placeholder: select_partners,
    createTag: function (params) {
      let term = params.term.trim();
      if (term === '') return null;
      return {
        id: term,
        text: term,
        newTag: true
      };
    }
  });

  let learning = $("#learning");
  if (learning.val() > 0) {
    $("#learning_container").hide();
  }
  hide_duplicate_headers();

  $("#activity_associated").on("change", toggle_tab);
  toggle_tab();
});

function toggle_tab() {
  let activity_associated = $("#activity_associated option:selected").data("poa_area");

  if (activity_associated === undefined || activity_associated === null || activity_associated === "") {
    return;
  }

  if (!activity_associated) {
    document.getElementById("nav_Strategic").style.display = "none";
    document.getElementById("nav_Learning").style.display = "none";
    document.getElementById("next_strategic").classList.add("invisible_field");
    document.getElementById("submit_report_from_quantitative").classList.remove("invisible_field");
  } else {
    document.getElementById("nav_Strategic").style.display = "block";
    document.getElementById("nav_Learning").style.display = "block";
    document.getElementById("next_strategic").classList.remove("invisible_field");
    document.getElementById("submit_report_from_quantitative").classList.add("invisible_field");
  }
}

function toggle_field(selectObject) {
  $("." + selectObject).toggleClass("invisible_field");
}

function openTab(evt, section) {
  let i, tab_content, tab_links;

  tab_content = document.getElementsByClassName("tab_content");
  for (i = 0; i < tab_content.length; i++) {
    tab_content[i].style.display = "none";
  }

  tab_links = document.getElementsByClassName("tab_links");
  for (i = 0; i < tab_links.length; i++) {
    tab_links[i].classList.remove("active");
  }

  $("#" + section)[0].style.display = "block";
  $("#nav_" + section)[0].classList.add("active");
}

$("#submit_report, #nav_submit_report, #submit_report_from_quantitative").click(function (event) {
  event.preventDefault();
  validateForm();
});

function focus_is_empty(input_) {
  return input_.val() === "";
}

function focus_and_switch(tab, focus_selector_or_fn) {
  tab.click();
  setTimeout(function () {
    let target = typeof focus_selector_or_fn === "function"
      ? focus_selector_or_fn()
      : $(focus_selector_or_fn);
    target.focus();
  }, 50);
}

function admin_field_missing(form, admin_fields) {
  for (const field of admin_fields) {
    if (focus_is_empty(form.find(field))) {
      return field;
    }
  }
  return null;
}

function no_metric_selected() {
  return $("#metrics_fieldset input[type='checkbox']:checked").length === 0
    && $("#metrics_fieldset input[type='radio']:checked").length === 0;
}

function no_direction_selected() {
  return $("#directions_fieldset input[type='checkbox']:checked").length === 0;
}

function no_strategic_question_selected() {
  return $("#strategic_questions_fieldset input[type='checkbox']:checked").length === 0;
}

function learning_field_missing(form, learning_fields) {
  for (const field of learning_fields) {
    if (focus_is_empty(form.find(field))) {
      return field;
    }
  }
  return null;
}

function validateForm() {
  let form = $("#report");
  let admin_tab = $("#nav_Administrative");
  let quantitative_tab = $("#nav_Quantitative");
  let strategy_tab = $("#nav_Strategic");
  let learning_tab = $("#nav_Learning");
  let admin_fields = ["#activity_associated", "#area_responsible", "#initial_date", "#description", "#links"];
  let learning_fields = ["#learning"];
  let activity_associated = form.find("#activity_associated option:selected").data("poa_area");

  let missing_admin_field = admin_field_missing(form, admin_fields);
  if (missing_admin_field) {
    focus_and_switch(admin_tab, () => form.find(missing_admin_field));
    return;
  }

  if (no_metric_selected()) {
    focus_and_switch(quantitative_tab, () => $("#metrics_fieldset input").first());
    return;
  }

  if (activity_associated !== 1) {
    form.submit();
    return;
  }

  if (no_direction_selected()) {
    focus_and_switch(strategy_tab, () => $("#directions_fieldset input[value=1]"));
    return;
  }

  if (no_strategic_question_selected()) {
    focus_and_switch(learning_tab, () => $("#strategic_questions_fieldset input[value=1]"));
    return;
  }

  let learning = $("#learning");
  if (learning.data("has_learning")) {
    if (learning.val() === 0 || learning.val().length < 500) {
      learning_tab.click();
      learning.focus();
      return;
    }

    let missing_learning_field = learning_field_missing(form, learning_fields);
    if (missing_learning_field) {
      learning_tab.click();
      form.find(missing_learning_field).focus();
      return;
    }
  }

  form.submit();
}

function show_metrics_options() {
  let activity_associated = $("#activity_associated").val();
  let funding_associated = $("#funding_associated").val();
  let metrics_related = metrics_set;

  if (activity_associated || funding_associated) {
    $.ajax({
      url: get_metrics_url,
      method: 'GET',
      dataType: 'json',
      data: { activity: activity_associated, fundings: funding_associated, instance: report_id },
      success: function (response) {
        let learning = $("#learning");
        let learning_container = $("#learning_container");
        let inner_html = "<fieldset id='metrics_fieldset' class='sub_container'><div style='overflow-y:scroll; max-height:200px'>";

        if (response["objects"]) {
          response["objects"].forEach(function (projectEl) {
            inner_html += "<div class='w3-container field_title' style='color:var(--main-color);'>" + projectEl["project"] + "</div>";
            projectEl["metrics"].forEach(function (metric) {
              let checked = "";
              let button_type = "checkbox";
              let check_style = "";

              if (metrics_related.indexOf(metric.id) >= 0) {
                checked = "checked";
              }
              if (projectEl["main"]) {
                button_type = "radio";
                check_style = "radio-checkmark";
              }

              let metric_label = metric.text;
              let metric_element = "<label class='select-container'>" + metric_label +
                "<input type='" + button_type + "' name='metrics_related' value='" + metric.id +
                "' " + checked + ">" + "<span class='checkmark " + check_style + "'></span></label>";
              inner_html += metric_element;
            });
          });
          inner_html += "</div></fieldset>";
          $("#metrics_to_select").html(inner_html);
        }

        if (response["main"]) {
          learning.data("has_learning", true);
          learning_container.show();
        } else {
          learning.data("has_learning", false);
          learning_container.hide();
        }
      },
      error: function (response) {
        console.log(response);
      }
    });
  }
}

function hide_duplicate_headers() {
  let operation_headers = $(".operation-header");
  let unique_elems = {};
  operation_headers.each(function () {
    let content = $(this).text().trim();
    if (unique_elems[content]) {
      $(this).hide();
    } else {
      unique_elems[content] = true;
    }
  });
}

document.getElementById("report").addEventListener("submit", function (event) {
  document.getElementById("submit_report").disabled = true;
  document.getElementById("nav_submit_report").disabled = true;
});