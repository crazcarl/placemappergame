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
			 // This creates the AJAX connection
			 $.ajax({
				 type: "POST",
				 url: "/",
				 data: data,
				 dataType: 'json',
				 success: function(data) {
					evaluateResult(data)
				 }
			 });
			});
		});
		
		function evaluateResult(data) {
			var correctDiv = document.getElementById('correct');
			var spanTag = document.createElement('span');
			if (data.correct == "True") {
				spanTag.setAttribute('class','glyphicon glyphicon-ok');
				spanTag.setAttribute('title',$("#barname").text());
				$('#distance').html("<strong>You got it!</strong>")
			}
			else {
				spanTag.setAttribute('class','glyphicon glyphicon-remove');
				spanTag.setAttribute('title',$("#barname").text());
				var output = "<strong>You were off by " + data.distance + " meters.</strong>"
				$('#distance').html(output);
			};
			correctDiv.appendChild(spanTag);
			if (barslist['bars'].length > 0) {
				$('#barname').html(barslist['bars'].pop());
			}
			else {
					window.location.href = "/gameover";
			};
			$('#score').html("Score: " + data['score'][0] + " / " + data['score'][1]);
		}
	