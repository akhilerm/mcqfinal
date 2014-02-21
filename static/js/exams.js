//llog = console.log;

var tstart = 0, htimer=false;

var examStat = {
	'qno'		: '',			
	'answerqno'	: '',
	'answer'	: '',
	'answertime': 0,
	'timeleft'	: parseInt('{{MAX_EXAM_SECS}}')						
};

function updateClock(){
	mins = Math.floor(examStat.timeleft / 60);
	secs = Math.floor(examStat.timeleft % 60);
	$('#minute').text((mins<10?'0':'')+mins);
	$('#second').text((secs<10?'0':'')+secs);	
}

function countdown(){
	examStat.timeleft-=1;
	updateClock();
	if(examStat.timeleft<1){
		clearInterval(htimer);
		window.location='/completed';
	}				
}

function loadStatus(){
	$.get('/api/qstatus',function(ret){
		$('#qstatus').html(ret).fadeIn().removeClass('hide');		  	
	});
}

function setQuestion(quests,choice,selected){
	$('#quest-no').text(examStat.answerqno);
	$('#question').html(quests);
	$('input[name=answer]').each(function(i,e){
		$(e).parent().text(choice[i]).prepend(e);
		e.cheked=false;
		$('input[name=answer]:checked').prop('checked', false);
	});
	if(selected)
		$('input[value='+selected+']').prop('checked', true);

}

function _loadQuestion(qno){
	examStat.qno = qno;
	if(!examStat.answer) examStat.answer=0;
	if(htimer) clearInterval(htimer); 
	$('#tspinner').fadeIn().prev().html('');	
	$.post('api/exam',examStat,function(ret){
		if(!ret.err){
			examStat.answerqno = ret.qno;
			setQuestion(ret.question,ret.choices,ret.answer);
			examStat.timeleft = ret.timeleft;
			updateClock();
			$('#tspinner').hide();			
			htimer = window.setInterval(countdown,1000);
		}else{
			alert(ret.err);
			if (ret.redirect) window.location = ret.redirect;
		}
		
	},'json');
	return false;		
}

function loadQuestion(qid){
	examStat.answer = 0;
	examStat.answertime = 0;
	return _loadQuestion(qid);	
}

function answerAndLoadQuestion(qid){
	examStat.answer = $('input[name=answer]:checked').val();
	if(examStat.answer) $('#qstatus a[href='+examStat.answerqno+']').addClass('answered');
	examStat.answertime = new Date().getTime();
	return _loadQuestion(qid);	
}

$(document).ready(function() {	
	$('#submit').click(function(){
		if($('input[name=answer]:checked').val())						
			return answerAndLoadQuestion('submit');
		else{
			alert('Please choose an answer');
			return false;
		}
	});
	
	$('#pass').click(function(){
		$('input[name=answer]:checked').prop('checked', false);
		return loadQuestion('pass');
	});
	
	$('#complete').click(function(){
		if(confirm('Finish exam ?'))
			window.location='/completed';
	});
	
	$('#qstatus').on('click','a',function(){
		loadQuestion($(this).attr('href'));
		return false;				
	});
	
	loadStatus();
	loadQuestion(1);			
});



 


//setQuestion('asdasd',['asdasd','2asdasdas','asdasdasdawewe3','4sdsdsdsada3423423 23423 23423 4 23423 42q34 234 234a']);
