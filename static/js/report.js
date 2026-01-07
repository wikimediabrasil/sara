$(document).ready(function () {
  $('.toggle__input.wiki').each(function () {
    if (this.checked) {
      toggle_field(this.id);
    }
  })
  show_metrics_options();
  $(".select-with-text").select2();

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

function validateForm() {
  let form = $("#report");
  let admin_tab = $("#nav_Administrative");
  let operations_tab = $("#nav_Operational");
  let quantitative_tab = $("#nav_Quantitative");
  let strategy_tab = $("#nav_Strategic");
  let learning_tab = $("#nav_Learning");
  let admin_fields = ["#activity_associated", "#area_responsible", "#initial_date", "#description", "#links"];
  let learning_fields = ["#learning"];
  let activity_associated = form.find("#activity_associated option:selected").data("poa_area")

  for (let i = 0; i < admin_fields.length; i++) {
    if (focus_is_empty(form.find(admin_fields[i]), admin_tab)) {
      admin_tab.click();
      setTimeout(function () {
        form.find(admin_fields[i])[0].focus();
      }, 50);
      return;
    }
  }

  if ($("#metrics_fieldset input[type='checkbox']:checked").length === 0 && $("#metrics_fieldset input[type='radio']:checked").length === 0) {
    quantitative_tab.click();
    setTimeout(function () {
      $("#metrics_fieldset input").first()[0].focus();
    }, 50);
    return;
  }

  if (activity_associated === 1) {
    if ($("#directions_fieldset input[type='checkbox']:checked").length === 0) {
      strategy_tab.click();
      setTimeout(function () {
        $("#directions_fieldset input[value=1]").focus();
      }, 50);
      return;
    }

    if ($("#strategic_questions_fieldset input[type='checkbox']:checked").length === 0) {
      learning_tab.click();
      setTimeout(function () {
        $("#strategic_questions_fieldset input[value=1]").focus();
      }, 50);
      return;
    }

    let learning = $("#learning");
    let has_learning = learning.data("has_learning");
    if (has_learning) {
      if (learning.val() === 0 || learning.val().length < 500) {
        learning_tab.click();
        learning.focus();
        return;
      }

      for (let i = 0; i < learning_fields.length; i++) {
        if (focus_is_empty(form.find(learning_fields[i]))) {
          learning_tab.click();
          form.find(learning_fields[i]).focus();
          return;
        }
      }
    }
  }

  form.submit();
}

function show_metrics_options() {
  let activity_associated = $("#activity_associated").val();
  let funding_associated = $("#funding_associated").val();
  let report_id = report_id;
  let metrics_related = metrics_set;

  if (activity_associated || funding_associated) {
    $.ajax({
      url: get_metrics_url,
      method: 'GET',
      dataType: 'json',
      data: {activity: activity_associated, fundings: funding_associated, instance: report_id},
      success: function (response) {
        let learning = $("#learning");
        let learning_container = $("#learning_container");
        let inner_html = "<fieldset id='metrics_fieldset' class='sub_container'><div style='overflow-y:scroll; max-height:200px'>";
        if (response["objects"]) {
          response["objects"].forEach(function (projectEl) {
            inner_html += "<div class='w3-container field_title' style='color:var(--main-color);'>" + projectEl["project"] + "</div>"
            projectEl["metrics"].forEach(function (metric) {
              let checked = "";
              let button_type = "checkbox";
              let check_style = "";
              if (jQuery.inArray(metric.id, metrics_related) >= 0) {
                checked = "checked";
              }
              if (projectEl["main"]) {
                button_type = "radio";
                check_style = "radio-checkmark";
              }
              let metric_label = (projectEl["lang"] === "en") ? metric.text_en : metric.text;
              let metric_element = "<label class='select-container'>" + metric_label +
                "<input type='" + button_type + "' name='metrics_related' value='" + metric.id +
                "' " + checked + ">" + "<span class='checkmark " + check_style + "'></span></label>"
              inner_html += metric_element
            })
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
        console.log(response)
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