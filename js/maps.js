	  var b2long = "";
	  var b2lat = "";
	  var barslist = {}
	  var barlist = {}
	  $(document).ready(function() {
		//grab list of bars here and set up first one.
		$.ajax({
			type: "GET",
			url: "/getbarlist",
			data: barlist,
			dataType: 'json',
			async: false,
			success: function(barlist) {
				var newbar = barlist['bars'].pop()
				$('#barname').html(newbar);
				barslist = barlist
			}
		 });
		$('#submit').click(function(){
			 if (markers.length == 0) {
				alert("Click the map at the bar's location before hitting submit. Click help in the bottom left for more details");
				return};  // No marker
			 // temporarily disable button to prevent duplicate submissions
			 $('#submit').attr('disabled',true)
			 
			 // remove marker and line if user clicks submit without moving marker
			 if (resultLine) {resultLine.setMap(null)};
			 if (resultMarker) {resultMarker.setMap(null)};
			 
			 //1. Get name of bar and pass as json array to server
			 var barname = {"barname":$("#barname").text()};
			 
			 //2. Get lat and long of bar for comparison
			 var bar2 = $.ajax({
				type: "GET",
				url: "/getbarlatlong",
				data: barname,
				dataType: 'json',
				async: false
			 });
		 	 bar2.success(function(data) {
				b2long = data.long;
				b2lat = data.lat;
			 });
			 // Create gmaps position object
			 var bar= new google.maps.LatLng(b2lat,b2long);
			 
			 // Grab position of marker
			 var location = markers[0].getPosition();
			 
			 //compare distance between marker and specified bar
			 var distance=google.maps.geometry.spherical.computeDistanceBetween(bar, location);
			 var data={"distance":distance,"barname":$("#barname").text()};
			 
			 // Submit the distance
			 $.ajax({
				 type: "POST",
				 url: "/",
				 data: data,
				 dataType: 'json',
				 success: function(data) {
					evaluateResult(data,bar,location)
					$('#submit').attr('disabled',false)
				 }
			 });
			});
		});
		
		function evaluateResult(data,bar,location) {
			if (data.correct == "True") {
				$('#distance').html("<strong>You got it!</strong>")
			}
			else {
				var output = "<strong>You were off by " + data.distance + " meters.</strong>"
				$('#distance').html(output);
				//draw a line from marker to correct location
				resultLine = new google.maps.Polyline({
				 path: [bar,location]
				 });
				 resultMarker = new google.maps.Marker({
						position: bar,
						map: map,
						icon: 'http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2%7C1dec36'
					});
				 resultLine.setMap(map);
				 resultMarker.setMap(map);
			};

			if (barslist['bars'].length > 0) {
				$('#barname').html(barslist['bars'].pop());
			}
			else {
					window.location.href = "/gameover";
			};
			// Update the score on the top right
			gg = document.getElementById('goodGlyph');
			bg = document.getElementById('badGlyph');
			gg.setAttribute('class','glyphicon glyphicon-ok');
			bg.setAttribute('class','glyphicon glyphicon-remove');
			$('#divider').html('/');
			$('#goodScore').html(data['score'][0]);
			bs = data['score'][1] - data['score'][0]
			$('#badScore').html(bs);
			
			// Display message after 5 to submit score or keep going
			if (parseInt(data['score'][1]) == 5) {
				$('#gameModal').modal('show');
			}
		}
	