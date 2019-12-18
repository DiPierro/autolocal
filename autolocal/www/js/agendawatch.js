$(document).ready(function() {
  var customerDetailsViewModel = function() {
    var self = this;
    self.id = ko.observable("");
    self.id2 = ko.observable("");
    self.keywords = ko.observableArray("");
    self.SuccessMessage = ko.observable("");
    self.municipalities = ko.observableArray([]);
    self.unsubscribe = function () {
      var CustomerDetail = {
        email_address: self.id2(),
      }
      $.ajax({
        url: 'https://cors-anywhere.herokuapp.com/https://9k2fkcj7pb.execute-api.us-west-1.amazonaws.com/prod/unsubscribeQuery',
        cache: false,
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        data: ko.toJSON(CustomerDetail),
        success: function (data) {
          self.SuccessMessage(data["body"])
          self.id2('');
        }
      }).fail(function(xhr, textStatus, err){
        alert("Error happened "+err);
      });
    };
    self.POSTautoLocalNews = function () {
      var failed = false;
      var the_municipalities = [];
      checkboxes = document.getElementsByName('foo');
      for(var i=0, n=checkboxes.length;i<n;i++) {
        if(checkboxes[i].checked == true) {
          the_municipalities.push(checkboxes[i].value);
        }
      }
      var CustomerDetail = {
        email_address: self.id(),
        keywords: self.keywords().split(','),
        municipalities: the_municipalities,
      }
      $.ajax({
        url: 'https://cors-anywhere.herokuapp.com/https://2nr3b6lltj.execute-api.us-west-1.amazonaws.com/prod/subscribeQuery',
        cache: false,
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        data: ko.toJSON(CustomerDetail),
        success: function (data) {
          self.SuccessMessage(data["body"])
          self.id('');
          self.keywords('');
          self.municipalities('');
        }
      }).fail(function(xhr, textStatus, err){
        failed = true;
        alert("Error happened "+err);
      });
      //if(failed==false)window.location.href = "landing.html";
    };
  }
  var viewModel = new customerDetailsViewModel();
  ko.applyBindings(viewModel);
});