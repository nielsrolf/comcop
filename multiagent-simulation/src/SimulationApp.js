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
    const response = await fetch('http://localhost:8000/init_world', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(worldStates[worldStates.length - 1] || { agents: [], games: [] }),
    });
    if (response.ok) {
      startSimulation();
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
      console.log('WebSocket closed. Attempting to reconnect...');
      setTimeout(startSimulation, 1000);
    };
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const drawWorld = (state) => {
    if (!canvasRef.current || !state) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw agents
    state.agents.forEach(agent => {
      ctx.beginPath();
      ctx.arc(
        agent.location[0] * canvas.width, 
        agent.location[1] * canvas.height, 
        Math.max(2, Math.min(10, agent.resources / 10)), // Size based on resources, min 2, max 10
        0, 
        2 * Math.PI
      );
      ctx.fillStyle = agent.color;
      ctx.fill();
    });

    // Draw games
    state.games.forEach(game => {
      ctx.fillStyle = 'black';
      ctx.fillRect(game.location[0] * canvas.width - 5, game.location[1] * canvas.height - 5, 10, 10);
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
      const newState = { ...lastState };

      if (selectedEntity === 'PrisonersDilemma') {
        newState.games = [...newState.games, { type: 'PrisonersDilemma', location: [x, y] }];
      } else {
        newState.agents = [...newState.agents, { 
          type: selectedEntity, 
          location: [x, y],
          resources: 10, // Initial resources
          color: selectedEntity === 'RandomAgent' ? 'blue' : 
                 selectedEntity === 'CooperateBot' ? 'green' : 'red'
        }];
      }

      const newStates = [newState];
      setCurrentStep(0);
      return newStates;
    });
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
    <div className="p-4 flex">
      <Card className="mr-4">
        <CardHeader>Multiagent Simulation</CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex space-x-4">
              <Select value={selectedEntity} onValueChange={setSelectedEntity}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select entity to place" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="RandomAgent">Random Agent</SelectItem>
                  <SelectItem value="CooperateBot">Cooperate Bot</SelectItem>
                  <SelectItem value="DefectBot">Defect Bot</SelectItem>
                  <SelectItem value="PrisonersDilemma">Prisoner's Dilemma Game</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={initWorld}>Initialize and Run Simulation</Button>
            </div>
            <canvas 
              ref={canvasRef} 
              width={500} 
              height={500} 
              className="border border-gray-300" 
              onClick={handleCanvasClick}
            />
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