import aiortc
import aiortc.contrib.media
import aiortc.sdp
from fastapi import APIRouter, Request, Response, HTTPException
import server_engine.state as state
from server_engine.tracking import tracker

router = APIRouter()

relay = aiortc.contrib.media.MediaRelay()

@router.post("/whip")
async def whip(request: Request):
    state.pc = aiortc.RTCPeerConnection()

    @state.pc.on("track")
    def on_track(track):
        print(f"Stream Track received: {track.kind}")
        if track.kind == "video":
            state.ingest_video_track = relay.subscribe(track)
            tracker.reset()
            print("Video Ingest Found. Beginning Inference.")

    @state.pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Stream Connection Change: {state.pc.connectionState}")
        if state.pc.connectionState == "failed" or state.pc.connectionState == "closed":
            await state.pc.close()

    offer = aiortc.RTCSessionDescription(
        sdp=(await request.body()).decode(), type="offer"
    )
    await state.pc.setRemoteDescription(offer)
    answer = await state.pc.createAnswer()
    await state.pc.setLocalDescription(answer)

    return Response(
        state.pc.localDescription.sdp,
        status_code=201,
        media_type="application/sdp",
        headers={"Location": "/whip/obs"},
    )

@router.patch("/whip/obs")
async def whip_trickle(request: Request):
    if not state.pc:
        raise HTTPException(status_code=404)

    sdpfragment = (await request.body()).decode()
    for line in sdpfragment.splitlines():
        if line.startswith("a=candidate:"):
            cand = aiortc.sdp.candidate_from_sdp(line[2:])
            await state.pc.addIceCandidate(cand)

    return Response(status_code=204)
