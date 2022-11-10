$(document).ready(function () {
    const MY_SESSION_STORAGE_KEY = 'my-sessions';

    var sessions = [];
    var sessionsMap = {};
    var mySessions = [];

    function loadSessions(callback){
        $.getJSON('sessions.json', callback);
    }

    function addSession(sessionId){
        mySessions = localStorage.getItem(MY_SESSION_STORAGE_KEY);

        if(!mySessions){
            mySessions = {}
        }else{
            try{
                mySessions = JSON.parse(mySessions);
            }catch{
                mySessions = {};
            }
        }

        if(!(sessionId in mySessions)){
            mySessions[sessionId] = {
                color: "primary"
            };
        }

        localStorage.setItem(MY_SESSION_STORAGE_KEY, JSON.stringify(mySessions));
    }

    function removeSession(sessionId){
        mySessions = localStorage.getItem(MY_SESSION_STORAGE_KEY);

        if(!mySessions){
            mySessions = {}
        }else{
            try{
                mySessions = JSON.parse(mySessions);
            }catch{
                mySessions = {};
            }
        }

        if(sessionId in mySessions){
            delete mySessions[sessionId];
        }

        localStorage.setItem(MY_SESSION_STORAGE_KEY, JSON.stringify(mySessions));
    }

    function changeSessionAttribute(sessionId, attribute, value){
        if(sessionId in mySessions){
            mySessions[sessionId][attribute] = value;

            localStorage.setItem(MY_SESSION_STORAGE_KEY, JSON.stringify(mySessions));
        }
    }

    function clearMySessions(){
        mySessions = {}
        localStorage.setItem(MY_SESSION_STORAGE_KEY, JSON.stringify(mySessions));
    }

    var calendarEl = $('#calendar')[0];
    var calendar = new FullCalendar.Calendar(calendarEl, {
        headerToolbar: {
            left: 'prev,next',
            center: 'title',
            right: 'timeGridWeek,customView'
        },
        views: {
            customView: {
                type: 'timeGridWeek',
                duration: { days: 1 },
                buttonText: 'day'
            }
        },
        initialView: 'timeGridWeek',
        initialDate: '2022-11-28',
        timeZone: 'America/Los_Angeles',
        scrollTime: '08:00:00',
        height: 600,
        eventDidMount: function(info) {
            $(info.el).popover({
                content: '<div class="popover-event-close-button-row">    <a href="#" class="btn btn-sm popover-event-close-button p-0" role="button"aria-pressed="true">        <span aria-hidden="true">&times;</span>    </a></div><div class="fw-bold">Code:</div><div class="popover-event-code"></div><p></p><div class="fw-bold">Title:</div><div class="popover-event-title"></div><p></p><div class="fw-bold">Type:</div><div class="popover-event-type"></div><p></p><div class="fw-bold">Venue:</div><div class="popover-event-venue"></div><p></p><div class="fw-bold">Change color:</div><div class="btn-group btn-group-sm" role="group" aria-label="Basic example">    <a type="button" class="btn btn-primary popover-event-color-change primary">Blue</a>    <a type="button" class="btn btn-success popover-event-color-change success">Green</a>    <a type="button" class="btn btn-warning popover-event-color-change warning">Yellow</a>    <a type="button" class="btn btn-secondary popover-event-color-change secondary">Grey</a></div>',
                html: true
            });
            
            $(info.el).on('show.bs.popover', function () {
                $('a').popover('hide');
            });

            $(info.el).on('shown.bs.popover', function () {
                var sessionId = info.event.id;
                var session = sessionsMap[sessionId];
                
                $('.popover-body').data('sessionId', sessionId);
                $('.popover-event-code').html('<a class="session-link" target="_blank" href="https://portal.awsevents.com/events/reinvent2022/dashboard/event/sessions/' + session["alias"] + '">' + session["alias"] + '</a>');
                $('.popover-event-title').text(session["name"]);
                $('.popover-event-type').text(session["sessionType"]);
                $('.popover-event-venue').text(session["venueStr"]);
            });
        }
    });
    calendar.render();

    $('body').on('click', '.popover-event-color-change', function(event){
        var $target = $(event.target);
        var sessionId = $target.parents('.popover-body').data('sessionId');
        var color = "primary";

        if($target.hasClass("primary")){
            color = "primary";
        }else if($target.hasClass("success")){
            color = "success";
        }else if($target.hasClass("warning")){
            color = "warning";
        }else if($target.hasClass("secondary")){
            color = "secondary";
        }

        setSessionColor(sessionId, color);
    });

    $('body').on('click', '.popover-event-close-button', function(event){
        $('a').popover('hide');
    });

    $('#session-table thead tr')
        .clone(true)
        .addClass('filters')
        .appendTo('#session-table thead');

    var table = $('#session-table').DataTable({
        columns: [
            {
                data: 'alias',
                render: function ( data, type, row, meta ) {
                    if(!!data){
                        return '<a onclick="event.stopPropagation()" class="session-link" target="_blank" href="https://portal.awsevents.com/events/reinvent2022/dashboard/event/sessions/' + data + '">' + data + '</a>';
                    }else{
                        return data;
                    }
                }
            },
            { data: 'name', width: "15%" },
            { data: 'sessionType' },
            { data: 'level' },
            { data: 'tracks' },
            { data: 'venue' },
            { data: 'startTime' },
            { data: 'endTime' },
            { data: 'reservable', width: "1%" },
            { data: 'reservableRemaining' },
            { data: 'waitlistRemaining' },
            { data: 'description', visible: false }
        ],
        rowId: 'sessionId',
        orderCellsTop: true,
        fixedHeader: true,
        rowCallback: function (row, data) {
            if(data["sessionId"] in mySessions){
                $(row).addClass('selected');
            }
        },
        initComplete: function () {
            var api = this.api();

            // For each column
            api
                .columns()
                .eq(0)
                .each(function (colIdx) {
                    // Set the header cell to contain the input element
                    var cell = $('.filters th').eq(
                        $(api.column(colIdx).header()).index()
                    );
                    var title = $(cell).text();
                    if(!title.length){
                        return true;
                    }

                    $(cell).html('<input type="text" class="form-control" placeholder="Search ' + title + '" />');

                    // On every keypress in this input
                    $(
                        'input',
                        $('.filters th').eq($(api.column(colIdx).header()).index())
                    )
                        .off('keyup change')
                        .on('change', function (e) {
                            // Get the search value
                            $(this).attr('title', $(this).val());
                            var regexr = '({search})'; //$(this).parents('th').find('select').val();

                            var cursorPosition = this.selectionStart;
                            // Search the column for that value
                            api
                                .column(colIdx)
                                .search(
                                    this.value != ''
                                        ? regexr.replace('{search}', '(((' + this.value + ')))')
                                        : '',
                                    this.value != '',
                                    this.value == ''
                                )
                                .draw();
                        })
                        .on('keyup', function (e) {
                            e.stopPropagation();

                            $(this).trigger('change');
                            $(this)
                                .focus()[0]
                                .setSelectionRange(cursorPosition, cursorPosition);
                        });
                });
        }
    });

    $('#session-table tbody').on('click', 'tr', function () {
        $(this).toggleClass('selected');
        var data = table.rows(this).data()[0];
        var sessionId = data["sessionId"];

        if($(this).hasClass('selected')){
            addSession(sessionId);
            addSessionToCalendar(sessionId);
        }else{
            removeSession(sessionId);
            removeSessionFromCalendar(sessionId);
        }
    });

    function refreshTable(){
        table.clear();

        var rows = []
        for(var i=0; i<sessions.length; i++){
            var session = sessions[i];

            var levelCode = "N/A";
            switch(session["level"]){
                case "beginner":
                    levelCode = "100"
                    break;
                case "intermediate":
                    levelCode = "200"
                    break;
                case "advanced":
                    levelCode = "300"
                    break;
                case "expert":
                    levelCode = "400"
                    break;
            }

            var tracks = [];
            for(var j=0; j<session["tracks"].length; j++){
                tracks.push(session["tracks"][j]["name"]);
            }

            var tracksStr = tracks.join("<br/>");

            var startTimeStr = "";
            var startTimeObj = null;
            if(session["startTime"]){
                startTimeObj = moment.utc(session["startTime"]).tz("America/Los_Angeles");
                startTimeStr = startTimeObj.format("YYYY-MM-DD HH:mm:ss");
            }

            var endTimeStr = ""
            var endTimeOnj = null;
            if(session["duration"] && startTimeObj){
                endTimeOnj = startTimeObj.clone().add(session["duration"], 'minutes');
                endTimeStr = endTimeOnj.format("YYYY-MM-DD HH:mm:ss");
            }

            var venueStr = getVenueStr(session);

            var reservableRemaining = "";
            var waitlistRemaining = "";
            var reservable = "N";

            if(!!session["capacities"]){
                if(session["capacities"]["reservableRemaining"] >= 0){
                    reservableRemaining = session["capacities"]["reservableRemaining"];

                    if(reservableRemaining > 0){
                        reservable = "Y";
                    }
                }

                if(session["capacities"]["waitlistRemaining"] >= 0){
                    waitlistRemaining = session["capacities"]["waitlistRemaining"];
                }
            }

            rows.push({
                "sessionId": session["sessionId"],
                "name": session["name"],
                "level": levelCode,
                "alias": session["alias"],
                "sessionType": session["sessionType"]["name"],
                "description": session["description"],
                "venue": venueStr,
                "tracks": tracksStr,
                "startTime": startTimeStr,
                "endTime": endTimeStr,
                "reservable": reservable,
                "reservableRemaining": reservableRemaining,
                "waitlistRemaining": waitlistRemaining
            })
        }

        table.rows.add(rows).draw();
    }

    function loadSessionsTime(){
        sessionsMap = {};
        for(var i=0; i<sessions.length; i++){
            var session = sessions[i];

            if(!session["sessionId"] || !session["alias"]){
                continue;
            }

            var sessionId = session["sessionId"];
            var alias = session["alias"];

            var startTimeStr = "";
            var startTimeObj = null;
            if(session["startTime"]){
                startTimeObj = moment.utc(session["startTime"]).tz("America/Los_Angeles");
                startTimeStr = startTimeObj.format("YYYY-MM-DD HH:mm:ss");
            }

            var endTimeStr = ""
            var endTimeOnj = null;
            if(startTimeObj && session["duration"]){
                endTimeOnj = startTimeObj.clone().add(session["duration"], 'minutes');
                endTimeStr = endTimeOnj.format("YYYY-MM-DD HH:mm:ss");
            }

            var venueStr = getVenueStr(session);
            var venue = null;
            if(session["venue"] && session["venue"]["name"]){
                venue = session["venue"]["name"]
            }

            sessionsMap[sessionId] = {
                "alias": alias,
                "name": session["name"],
                "startTime": startTimeStr,
                "endTime": endTimeStr,
                "venueStr": venueStr,
                "venue": venue,
                "sessionType": session["sessionType"]["name"]
            };
        }
    }

    function addSessionToCalendar(sessionId, color){
        if(!(sessionId in sessionsMap)){
            return;
        }
        
        var session = sessionsMap[sessionId];

        var alias = session["alias"];
        var name = session["name"];
        var startTime = session["startTime"];
        var endTime = session["endTime"];
        var venue = session["venue"];

        if(calendar.getEventById(alias)){
            calendar.getEventById(alias).remove();
        }

        var colorCodes = getColorCodes(color, venue);
        if(!colorCodes[2]){
            colorCodes[2] = colorCodes[0];
        }

        calendar.addEvent({
            title: alias + ' - ' + name,
            id: sessionId,
            start: startTime,
            end: endTime,
            backgroundColor: colorCodes[0],
            textColor: colorCodes[1],
            borderColor: colorCodes[2]
        });
    }

    function removeSessionFromCalendar(sessionId){
        if(calendar.getEventById(sessionId)){
            calendar.getEventById(sessionId).remove();
        }
    }

    function clearCalendar(){
        calendar.removeAllEvents();
    }

    function loadMySessions(){
        mySessions = localStorage.getItem(MY_SESSION_STORAGE_KEY);
        var newMySessions = {};
        var isOldFormat = false;

        if(!mySessions){
            mySessions = {}
        }else{
            try{
                mySessions = JSON.parse(mySessions);
            }catch{
                mySessions = {};
            }
        }

        if(mySessions.length == 0){
            mySessions = {};
            isOldFormat = true;
        }

        for(var sessionId in mySessions){
            var color = "primary";

            if(sessionId.length < 10){
                isOldFormat = true;
                
                sessionId = mySessions[sessionId];
                newMySessions[sessionId] = {
                    color: color
                };
            }else{
                color = mySessions[sessionId]["color"];
                newMySessions[sessionId] = mySessions[sessionId];
            }

            addSessionToCalendar(sessionId, color);
        }

        if(isOldFormat){
            mySessions = newMySessions;
            localStorage.setItem(MY_SESSION_STORAGE_KEY, JSON.stringify(mySessions));
        }
    }

    function getColorCodes(color, venue){
        var bgColor = "#3788d8";
        var textColor = "#fff";
        var borderColor = null;

        switch(color){
            case "primary":
                bgColor = "#3788d8";
                textColor = "#fff";
                break;

            case "success":
                bgColor = "#198754";
                textColor = "#fff";
                break;

            case "warning":
                bgColor = "#ffc107";
                textColor = "#000";
                break;
            
            case "secondary":
                bgColor = "#6c757d";
                textColor = "#fff";
                break;
        }

        switch(venue){
            case "Mandalay Bay":
                borderColor = "#b400ff";
                break;
            
            case "Wynn":
                borderColor = "#000000";
                break;
            
            case "MGM Grand":
                borderColor = "#ffa8a8";
                break;
            
            case "Venetian":
                borderColor = "#ff0000";
                break;
            
            case "Caesars Forum":
                borderColor = "#00f1ff";
                break;
            
            case "Encore":
                borderColor = "#6cff00";
                break;
        }

        return [bgColor, textColor, borderColor];
    }

    function setSessionColor(sessionId, color){
        var session = sessionsMap[sessionId];
        var venue = session["venue"];
        var colorCodes = getColorCodes(color, venue);
        
        calendar.getEventById(sessionId).setProp("backgroundColor", colorCodes[0]);
        calendar.getEventById(sessionId).setProp("textColor", colorCodes[1]);

        if(colorCodes[2]){
            calendar.getEventById(sessionId).setProp("borderColor", colorCodes[2]);
        }else{
            calendar.getEventById(sessionId).setProp("borderColor", colorCodes[0]);
        }

        changeSessionAttribute(sessionId, "color", color);
    }

    function showMySessionsOnly(){
        var filteredData = table.data().filter(function(item){
            return item["sessionId"] in mySessions;
        });

        table.clear();
        table.rows.add(filteredData).draw();
    }

    $('#show-my-session-switch').change(function(){
        if($(this).is(":checked")){
            showMySessionsOnly();
        }else{
            refreshTable();
        }
    })

    function importMySessions(aliasStr){
        var aliases = [];

        try{
            aliases = JSON.parse(aliasStr);
        }catch{
            return;
        }

        for(var i=0; i<aliases.length; i++){
            var alias = aliases[i];

            for(sessionId in sessionsMap){
                if(sessionsMap[sessionId]["alias"] == alias){
                    addSession(sessionId);
                    addSessionToCalendar(sessionId);
                }
            }
        }
    }

    function getVenueStr(session){
        var venueStr = "";
        if(session["venue"] && session["venue"]["name"]){
            venueStr += session["venue"]["name"];
        }

        if(session["room"] && session["room"]["name"]){
            venueStr += " - ";
            venueStr += session["room"]["name"];
        }

        if(venueStr.length == 0){
            venueStr = "N/A";
        }

        return venueStr;
    }

    $('#session-import-modal').on('show.bs.modal', function (e) {
        $('#session-import-input').val('');
    });

    $('#import-button').click(function(){
        var input = $('#session-import-input').val();
        importMySessions(input);

        showMySessionsOnly();
        $('#show-my-session-switch').prop("checked", true);
        $('#session-import-modal').modal('hide');
    })

    $('#confirm-clear-my-session-button').click(function(){
        clearMySessions();
        clearCalendar();
        refreshTable();

        $('#show-my-session-switch').prop("checked", false);
        $('#clear-my-session-modal').modal('hide');
    })

    loadSessions(function(data){
        sessions = data;

        loadSessionsTime();
        loadMySessions();
        refreshTable();
    });

    function exportICS(){
        var cal = ics();

        for(var sessionId in mySessions){
            var session = sessionsMap[sessionId];

            if(!session){
                continue;
            }

            var title = session["alias"] + " - " + session["name"];
            var location = session["venueStr"];
            location = location.replace(",", " ");
            
            var startTimeObj = null;
            if(session["startTime"]){
                startTimeObj = moment.tz(session["startTime"], "America/Los_Angeles");
            }

            var endTimeOnj = null;
            if(session["endTime"]){
                endTimeOnj = moment.tz(session["endTime"], "America/Los_Angeles");
            }

            if(!!startTimeObj && !!endTimeOnj){
                cal.addEvent(title, "", location, startTimeObj.format("YYYY-MM-DDTHH:mm:ss"), endTimeOnj.format("YYYY-MM-DDTHH:mm:ss"));
            }
        }

        cal.download("reinvent");
    }

    $('#export-ics-button').click(function(){
        exportICS();
    });
});
