import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader } from './components/ui/card';
import { Button } from './components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Slider } from './components/ui/slider';

const SimulationApp = () => {
  const [worldStates, setWorldStates] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState('RandomAgent');
  const [currentStep, setCurrentStep] = useState(0);
  const [populationPlot, setPopulationPlot] = useState(null);
  const [agentSpeed, setAgentSpeed] = useState(0.1);
  const [hoveredAgent, setHoveredAgent] = useState(null);
  const [isSimulationRunning, setIsSimulationRunning] = useState(false);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const initWorld = async () => {
    try {
      console.log('Sending init_world request...');
      const response = await fetch('http://localhost:8000/init_world', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(worldStates[worldStates.length - 1] || { agents: [], games: [] }),
      });
      console.log('Response received:', response.status);
      if (response.ok) {
        const data = await response.json();
        console.log('Init successful:', data);
        startSimulation();
      } else {
        console.error('Init failed:', response.status, await response.text());
      }
    } catch (error) {
      console.error('Error initializing world:', error);
    }
  };

  const startSimulation = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    wsRef.current = new WebSocket('ws://localhost:8000/ws');
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setWorldStates(prevStates => {
        const newStates = [...prevStates, data];
        setCurrentStep(newStates.length - 1);
        return newStates;
      });
    };
    wsRef.current.onclose = () => {
      console.log('WebSocket closed.');
      setIsSimulationRunning(false);
    };
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsSimulationRunning(false);
    };
    setIsSimulationRunning(true);
  };

  const stopSimulation = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsSimulationRunning(false);
  };

  const drawWorld = (state) => {
    if (!canvasRef.current ||!state) return;
  
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  
    // Draw games first
    state.games.forEach(game => {
      ctx.beginPath();
      ctx.arc(
        game.location[0] * canvas.width,
        game.location[1] * canvas.height,
        15, // Fixed size for games
        0,
        2 * Math.PI
      );
      ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
      ctx.fill();
      ctx.strokeStyle = 'black';
      ctx.stroke();
  
      // Draw PD icon
      ctx.fillStyle = 'black';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline ='middle';
      ctx.fillText('PD', game.location[0] * canvas.width, game.location[1] * canvas.height);
    });
  
    // Then draw agents
    state.agents.forEach(agent => {
      const size = Math.max(5, Math.min(20, agent.resources / 2)); // Size based on resources, min 5, max 20
      ctx.beginPath();
      ctx.arc(
        agent.location[0] * canvas.width, 
        agent.location[1] * canvas.height, 
        size,
        0, 
        2 * Math.PI
      );
      ctx.fillStyle = agent.color;
      ctx.fill();
    });
  };

  useEffect(() => {
    const currentState = worldStates[currentStep];
    drawWorld(currentState);
  }, [currentStep, worldStates]);

  const handleCanvasClick = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) / canvas.width;
    const y = (event.clientY - rect.top) / canvas.height;
  
    setWorldStates(prevStates => {
      const lastState = prevStates[prevStates.length - 1] || { agents: [], games: [] };
      const newState = {...lastState };
  
      if (selectedEntity === 'PrisonersDilemma') {
        newState.games = [...newState.games, { type: 'PrisonersDilemma', location: [x, y] }];
      } else {
        newState.agents = [...newState.agents, { 
          type: selectedEntity, 
          location: [x, y],
          resources: 10, // Initial resources
          speed: agentSpeed,
          color: selectedEntity === 'RandomAgent'? 'blue' : 
                 selectedEntity === 'CooperateBot'? 'green' : 
                 selectedEntity === 'DefectBot'?'red' : 
                 selectedEntity === 'MutatingBot'? 'purple' : 'black'
        }];
      }
  
      const newStates = [newState];
      setCurrentStep(0);
      return newStates;
    });
  };

  const handleCanvasHover = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) / canvas.width;
    const y = (event.clientY - rect.top) / canvas.height;

    const currentState = worldStates[currentStep];
    if (currentState) {
      const hoveredAgent = currentState.agents.find(agent => {
        const dx = agent.location[0] - x;
        const dy = agent.location[1] - y;
        return Math.sqrt(dx*dx + dy*dy) < 0.02; // Adjust this value to change hover sensitivity
      });
      setHoveredAgent(hoveredAgent);
    }
  };

  const handleSliderChange = (value) => {
    setCurrentStep(value[0]);
  };

  const fetchPopulationPlot = async () => {
    const response = await fetch('http://localhost:8000/population_plot');
    if (response.ok) {
      const blob = await response.blob();
      setPopulationPlot(URL.createObjectURL(blob));
    }
  };

  return (
    <div className="p-4 flex flex-col md:flex-row">
      <Card className="mr-4 mb-4 md:mb-0">
        <CardHeader>Multiagent Simulation</CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex flex-wrap space-x-4 space-y-2">
              <Select value={selectedEntity} onValueChange={setSelectedEntity}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select entity to place" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="RandomAgent">Random Agent</SelectItem>
                  <SelectItem value="CooperateBot">Cooperate Bot</SelectItem>
                  <SelectItem value="DefectBot">Defect Bot</SelectItem>
                  <SelectItem value="MutatingBot">Mutating Bot</SelectItem>
                  <SelectItem value="PrisonersDilemma">Prisoner's Dilemma Game</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={initWorld} disabled={isSimulationRunning}>Initialize and Run Simulation</Button>
              <Button onClick={stopSimulation} disabled={!isSimulationRunning}>Stop Simulation</Button>
            </div>
            <div className="flex items-center space-x-2">
              <span>Agent Speed:</span>
              <Slider
                value={[agentSpeed]}
                min={0.01}
                max={0.5}
                step={0.01}
                className="w-[200px]"
                onValueChange={(value) => setAgentSpeed(value[0])}
              />
              <span>{agentSpeed.toFixed(2)}</span>
            </div>
            <div className="relative">
              <canvas 
                ref={canvasRef} 
                width={500} 
                height={500} 
                className="border border-gray-300" 
                onClick={handleCanvasClick}
                onMouseMove={handleCanvasHover}
                onMouseLeave={() => setHoveredAgent(null)}
              />
              {hoveredAgent && (
                <div className="absolute top-0 left-0 bg-white p-2 border border-gray-300 rounded shadow">
                  <p>Resources: {hoveredAgent.resources?.toFixed(2) ?? 'N/A'}</p>
                  <p>Speed: {hoveredAgent.speed?.toFixed(2) ?? 'N/A'}</p>
                </div>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <span>Step: {currentStep}</span>
              <Slider
                value={[currentStep]}
                max={worldStates.length - 1}
                step={1}
                className="w-[200px]"
                onValueChange={handleSliderChange}
              />
            </div>
            <div>
              Agents: {worldStates[currentStep]?.agents.length || 0}, 
              Games: {worldStates[currentStep]?.games.length || 0}
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>Population Distribution</CardHeader>
        <CardContent>
          <Button onClick={fetchPopulationPlot}>
            {populationPlot ? 'Update Population Plot' : 'Render Population Plot'}
          </Button>
          {populationPlot && (
            <img src={populationPlot} alt="Population Distribution" className="mt-4" />
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SimulationApp;