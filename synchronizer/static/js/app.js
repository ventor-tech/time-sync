$(function() {
    $('#date_started_from, #date_started, #date_ended').datetimepicker({
        format: "YYYY-MM-DD HH:mm:ss",
        defaultDate: (new Date()).setHours(0,0,0,0),
        widgetPositioning: {
            vertical: 'bottom'
        }
    });
});