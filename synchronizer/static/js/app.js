$(function () {
    $('#date_started_from, #date_started, #date_ended').datepicker({
        format: "yyyy-mm-dd",
        orientation: 'bottom'
    }).datepicker('setDate', 'now');

    // Select2 AJAX for issue field
    $('#issue_id').select2({
        placeholder: 'Start typing...',
        ajax: {
            url: '/api/issues',
            dataType: 'json',
            method: 'GET',
            data: function (params) {
                let query = {
                    term: params.term,
                    sync_id: $(this).closest('form').find('#sync_id').val()
                }
                return query;
            }
        },
        minimumInputLength: 3
    });

    $(document).ready(function () {
        $('table').DataTable({
            columnDefs: [
                { type: 'natural', targets: '_all' }
            ]
        });
    });
});